# 🎯 Divination Generator API

Сервис для генерации интерпретаций рунических раскладов с использованием искусственного интеллекта. API позволяет получать детальные толкования рунических раскладов с учетом выбранной темы и статуса подписки.

## 🚀 Быстрый старт

### Требования
- Python 3.13+
- Poetry
- Docker (опционально)

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/divination-generator.git
cd divination-generator
```

2. Установите зависимости:
```bash
poetry install
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env, добавив необходимые ключи API
```

## 🏃‍♂️ Запуск

### Локальный запуск API
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Запуск через Docker
```bash
docker-compose up --build
```

## 📡 API Endpoints

### Интерпретация рунического расклада

#### Запрос
```bash
curl -X POST "http://localhost:8080/api/v1/divination/encode" \
     -H "Content-Type: application/json" \
     -d '{
           "runes": ["Иса", "Лагуз", "Вуньо"],
           "theme": "Карьера",
           "premium": false,
           "model": "deepseek-reasoner"
         }'
```

#### Ответ
```json
{
  "interpretation": "Сгенерированное описание расклада..."
}
```

### Проверка работоспособности сервиса
```bash
curl "http://localhost:8080/"
```

## 🏗 Структура проекта

```
divination-generator/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/    # API endpoints
│   │   ├── core/                 # Основная бизнес-логика
│   │   ├── data/                 # Данные и примеры
│   │   ├── monitoring/           # Конфигурация мониторинга
│   │   └── main.py              # Точка входа
│   ├── demo/                     # Streamlit демо
│   ├── docker-compose.yaml      # Docker конфигурация
│   └── pyproject.toml           # Зависимости проекта
```

## 🛠 Разработка

### Запуск тестов
```bash
poetry run pytest
```

## 📈 Мониторинг в Grafana

После запуска через Docker:
1. Откройте `http://localhost:3000`
2. Войдите с дефолтными креденшиалами (admin/admin)

### Доступные метрики

#### Системные метрики
- `default` - базовые метрики системы
- `latency` - время ответа API
- `requests` - количество запросов
- `response_size` - размер ответов

#### Бизнес-метрики
- `http_requests_by_premium_total` - статистика запросов по premium-статусу

## 🔒 Безопасность

- Все API ключи хранятся в переменных окружения
- Реализована базовая аутентификация для premium-функций
