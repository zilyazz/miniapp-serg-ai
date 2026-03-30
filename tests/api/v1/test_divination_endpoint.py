import pytest
import httpx
import respx
from fastapi import status
from fastapi.testclient import TestClient
import json

# Важно: импортировать приложение ПОСЛЕ установки моков или настроек тестов
# Если настройки читаются при импорте, их нужно переопределить до импорта app
from app.main import app
from app.core.config import settings
from app.api.v1.schemas import DivinationResponse

# Используем синхронный TestClient для простоты, но можно и асинхронный
client = TestClient(app)

# URL внешнего API для мокирования
DEEPSEEK_API_URL = f"{settings.deepseek_base_url}/chat/completions"

@pytest.fixture
def mock_deepseek_api():
    """Фикстура для мокирования ответов от DeepSeek API."""
    with respx.mock as mock:
        yield mock

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Создает временный файл примеров для тестов и переопределяет путь в настройках."""
    # Создаем временный файл с валидными примерами
    examples_content = {
        "1-2-3": {"runes": ["Феху", "Уруз", "Гебо"], "description": "Тестовый пример 1"},
        "4-5-6": {"runes": ["Ансуз", "Райдо", "Кеназ"], "description": "Тестовый пример 2"}
    }
    examples_file = tmp_path / "test_RuneExample.json"
    examples_file.write_text(json.dumps(examples_content, ensure_ascii=False), encoding='utf-8')

    # Переопределяем путь в настройках на время теста
    monkeypatch.setattr(settings, 'examples_file_path', str(examples_file))

    # Перезагружаем сервис, чтобы он подхватил новый путь (если он создается при импорте)
    # Это может потребовать более сложной логики управления зависимостями в реальном приложении
    # Пока предполагаем, что достаточно пересоздать сервис или мокнуть его
    # TODO: Улучшить управление зависимостями для тестирования


def test_interpret_success(mock_deepseek_api):
    """Тест успешного запроса интерпретации."""
    # Мокируем успешный ответ от DeepSeek
    mock_response_payload = {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "deepseek-chat",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "  Сгенерированная интерпретация.  "},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21}
    }
    mock_deepseek_api.post(DEEPSEEK_API_URL).mock(return_value=httpx.Response(
        status.HTTP_200_OK,
        json=mock_response_payload
    ))

    request_payload = {"runes": ["Феху", "Уруз"], "theme": "Тест"}
    response = client.post("/api/v1/divination/encode", json=request_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = DivinationResponse(**response.json())
    assert response_data.interpretation == "Сгенерированная интерпретация."
    assert mock_deepseek_api.calls.call_count == 1 # Проверяем, что API был вызван


def test_interpret_empty_runes(mock_deepseek_api):
    """Тест запроса с пустым списком рун (ожидаем ошибку валидации)."""
    request_payload = {"runes": [], "theme": "Тест"}
    response = client.post("/api/v1/divination/encode", json=request_payload)
    # FastAPI вернет 422 Unprocessable Entity для ошибок валидации Pydantic
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_interpret_missing_theme(mock_deepseek_api):
    """Тест запроса с отсутствующим полем theme (ожидаем ошибку валидации)."""
    request_payload = {"runes": ["Феху"]}
    response = client.post("/api/v1/divination/encode", json=request_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_interpret_deepseek_insufficient_balance(mock_deepseek_api):
    """Тест ошибки 402 (Insufficient Balance) от DeepSeek."""
    error_message = "Insufficient Balance"
    mock_deepseek_api.post(DEEPSEEK_API_URL).mock(return_value=httpx.Response(
        status.HTTP_402_PAYMENT_REQUIRED,
        json={"error": {"message": error_message, "type": "insufficient_funds"}} # Примерный формат
    ))

    request_payload = {"runes": ["Иса"], "theme": "Баланс"}
    response = client.post("/api/v1/divination/encode", json=request_payload)

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert error_message in response.json()["detail"]

def test_interpret_deepseek_rate_limit(mock_deepseek_api):
    """Тест ошибки 429 (Rate Limit) от DeepSeek."""
    error_message = "Rate limit exceeded"
    mock_deepseek_api.post(DEEPSEEK_API_URL).mock(return_value=httpx.Response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        json={"error": {"message": error_message, "type": "rate_limit"}}
    ))

    request_payload = {"runes": ["Лагуз"], "theme": "Лимит"}
    response = client.post("/api/v1/divination/encode", json=request_payload)

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert error_message in response.json()["detail"]


def test_interpret_deepseek_server_error(mock_deepseek_api):
    """Тест ошибки 5xx от DeepSeek (ожидаем 502 Bad Gateway от нашего API)."""
    error_message = "Internal Server Error on AI side"
    mock_deepseek_api.post(DEEPSEEK_API_URL).mock(return_value=httpx.Response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        json={"error": {"message": error_message, "type": "server_error"}}
    ))

    request_payload = {"runes": ["Гебо"], "theme": "Сервер"}
    response = client.post("/api/v1/divination/encode", json=request_payload)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Ошибка на стороне AI сервиса" in response.json()["detail"]
    assert error_message in response.json()["detail"]


def test_interpret_deepseek_connection_error(mock_deepseek_api):
    """Тест ошибки соединения с DeepSeek (ожидаем 502 Bad Gateway)."""
    mock_deepseek_api.post(DEEPSEEK_API_URL).mock(side_effect=httpx.ConnectError("Connection failed"))

    request_payload = {"runes": ["Вуньо"], "theme": "Соединение"}
    response = client.post("/api/v1/divination/encode", json=request_payload)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Ошибка подключения к AI сервису" in response.json()["detail"]


# Тест на ошибку загрузки файла примеров (требует настройки monkeypatch ДО импорта app/service)
# @pytest.mark.skip(reason="Требует настройки фикстуры для переопределения ДО импорта сервиса")
# def test_interpret_examples_load_error(monkeypatch):
#     """Тест ошибки 503 при проблеме с файлом примеров."""
#     # Мокаем путь к несуществующему файлу ДО импорта сервиса
#     monkeypatch.setattr(settings, 'examples_file_path', "/path/to/nonexistent/file.json")
    
#     # Нужно как-то перезагрузить сервис или импортировать app здесь
#     from app.main import app as test_app
#     local_client = TestClient(test_app)
    
#     request_payload = {"runes": ["Турисаз"], "theme": "Файл"}
#     response = local_client.post("/api/v1/divination/interpret", json=request_payload)
    
#     assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
#     assert "Сервис недоступен из-за ошибки конфигурации" in response.json()["detail"]


# Нужны дополнительные тесты: 
# - Пустой ответ от AI
# - Другие ошибки 4xx от AI -> соответствующий статус
# - Валидация типов в запросе (не строки в runes)
# - Проверка содержимого промпта, отправляемого в AI (сложнее, требует доступа к request в mock)
