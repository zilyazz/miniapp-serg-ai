from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import tarot
from app.core.models import AIError

client = TestClient(app)


def test_tarot_day_success(monkeypatch):
    captured = {}

    def fake_get_interpretation(*, prompt: str, model: str) -> str:
        captured['prompt'] = prompt
        captured['model'] = model
        return 'Это спокойный, собранный день, в котором карта подсказывает держаться внутренней опоры и не распыляться на лишнее. Чем яснее ты расставишь приоритеты, тем легче будет почувствовать контроль над происходящим.'

    monkeypatch.setattr(tarot.tarot_day_service, 'get_interpretation', fake_get_interpretation)

    response = client.post(
        '/api/v1/tarot/day',
        json={
            'prompt': 'Карта дня: Император (перевернутая)\nДай интерпретацию на русском языке.',
            'model': 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8',
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'interpretation': 'Это спокойный, собранный день, в котором карта подсказывает держаться внутренней опоры и не распыляться на лишнее. Чем яснее ты расставишь приоритеты, тем легче будет почувствовать контроль над происходящим.'
    }
    assert captured['prompt'] == 'Карта дня: Император (перевернутая)\nДай интерпретацию на русском языке.'
    assert captured['model'] == 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8'


def test_tarot_day_empty_prompt():
    response = client.post(
        '/api/v1/tarot/day',
        json={
            'prompt': '   ',
            'model': 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8',
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()['detail'] == 'Поле prompt обязательно для заполнения.'


def test_tarot_day_ai_error(monkeypatch):
    def fake_get_interpretation(*, prompt: str, model: str) -> str:
        raise AIError('Модель вернула слишком короткую интерпретацию для tarot day: 20 символов')

    monkeypatch.setattr(tarot.tarot_day_service, 'get_interpretation', fake_get_interpretation)

    response = client.post(
        '/api/v1/tarot/day',
        json={
            'prompt': 'Карта дня: Император',
            'model': 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8',
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert 'слишком короткую интерпретацию' in response.json()['detail']
