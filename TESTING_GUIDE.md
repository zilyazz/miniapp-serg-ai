# 📋 Инструкция по тестированию фичи "Совместимость"

## 🚀 Шаг 1: Запуск проекта через Docker

### 1.1. Перейдите в корневую папку проекта:
```bash
cd /Users/zilya/divination-generator/divination-generator
```

### 1.2. Остановите контейнеры (если они запущены):
```bash
docker-compose down
```

### 1.3. Соберите и запустите контейнеры:
```bash
docker-compose up --build
```

**Что происходит:**
- Собирается Docker-образ backend сервиса
- Запускается FastAPI приложение на порту 8080
- Запускается Prometheus (порт 9090)
- Запускается Grafana (порт 3000)
- Запускается Streamlit (порт 8501)

**Подождите** пока увидите сообщение типа:
```
backend    | INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

## 🧪 Шаг 2: Проверка что сервер запустился

### 2.1. Откройте в браузере Swagger UI:
```
http://localhost:8080/docs
```

Или просто корневой эндпоинт:
```
http://localhost:8080
```

Должно появиться сообщение:
```json
{"message": "Welcome to the Divination Generator API! Documentation is available at /docs"}
```

### 2.2. В Swagger UI вы должны увидеть 3 группы эндпоинтов:
- **Divination V1** - расклады
- **Sonnik V1** - сонник  
- **Compatibility V1** - совместимость ⭐ (наша новая фича!)

---

## 🎯 Шаг 3: Тестирование через Swagger UI (самый простой способ)

### 3.1. Откройте Swagger UI:
```
http://localhost:8080/docs
```

### 3.2. Найдите эндпоинт:
```
POST /api/v1/compatibility/analyze
```

### 3.3. Нажмите "Try it out"

### 3.4. Вставьте тестовый JSON в поле `request body`:

```json
{
  "data": {
    "mode": "romance",
    "score": 63,
    "label": "гармония",
    "person_a": {
      "name": "Илья",
      "gender": "male",
      "element": "fire"
    },
    "person_b": {
      "name": "Валерия",
      "gender": "female",
      "element": "earth"
    },
    "top_aspects": [
      {
        "a": "mars",
        "b": "venus",
        "type": "sextile",
        "weight": 12
      },
      {
        "a": "sun",
        "b": "venus",
        "type": "opposition",
        "weight": -10
      },
      {
        "a": "jupiter",
        "b": "asc",
        "type": "trine",
        "weight": 10
      },
      {
        "a": "moon",
        "b": "venus",
        "type": "square",
        "weight": -9
      },
      {
        "a": "mars",
        "b": "moon",
        "type": "square",
        "weight": -9
      },
      {
        "a": "saturn",
        "b": "sun",
        "type": "square",
        "weight": -9
      },
      {
        "a": "sun",
        "b": "asc",
        "type": "sextile",
        "weight": 9
      },
      {
        "a": "venus",
        "b": "asc",
        "type": "sextile",
        "weight": 9
      },
      {
        "a": "mercury",
        "b": "moon",
        "type": "conjunction",
        "weight": 7
      },
      {
        "a": "asc",
        "b": "jupiter",
        "type": "sextile",
        "weight": 7
      },
      {
        "a": "saturn",
        "b": "mercury",
        "type": "trine",
        "weight": 6
      },
      {
        "a": "jupiter",
        "b": "jupiter",
        "type": "sextile",
        "weight": 5
      }
    ],
    "stats": {
      "harmonious_count": 7,
      "challenging_count": 4,
      "has_asc": true
    }
  },
  "premium": false,
  "model": "Qwen/Qwen3-Next-80B-A3B-Instruct"
}
```

### 3.5. Нажмите "Execute"

### 3.6. Проверьте ответ:
Должен прийти ответ с полем `interpretation`, содержащим анализ совместимости в заданном формате.

---

## 🔧 Шаг 4: Тестирование через curl (альтернативный способ)

Откройте новый терминал (старый оставьте с запущенным docker-compose) и выполните:

```bash
curl -X POST "http://localhost:8080/api/v1/compatibility/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "mode": "friendship",
      "score": 65,
      "label": "гармония",
      "person_a": {
        "name": "Алексей",
        "gender": "male",
        "element": "fire"
      },
      "person_b": {
        "name": "Дмитрий",
        "gender": "male",
        "element": "water"
      },
      "top_aspects": [
        {
          "a": "sun",
          "b": "moon",
          "type": "trine",
          "weight": 10
        },
        {
          "a": "mars",
          "b": "mars",
          "type": "conjunction",
          "weight": 8
        }
      ],
      "stats": {
        "harmonious_count": 2,
        "challenging_count": 0,
        "has_asc": false
      }
    },
    "premium": false,
    "model": "Qwen/Qwen3-Next-80B-A3B-Instruct"
  }'
```

---

## 📊 Шаг 5: Проверка логов

### В терминале с docker-compose смотрите логи:

```bash
# Логи только backend сервиса:
docker-compose logs -f backend

# Все логи:
docker-compose logs -f
```

**Что должно быть в логах:**
- `INFO: Инициализация сервиса совместимости`
- `INFO: Получен запрос на анализ совместимости. Premium: False, Модель: Qwen/Qwen3-Next-80B-A3B-Instruct`
- `INFO: Отправка запроса к AI API для анализа совместимости...`
- `INFO: Ответ от AI API получен успешно.`
- `INFO: Сгенерирован анализ совместимости длиной ... символов.`

---

## ✅ Шаг 6: Что проверить в ответе

### Формат ответа должен быть:
1. **Заголовок:** "Суть за 10 секунд:"
   - 3 строки с ресурсами

2. **Интерпретация:**
   - 2-3 абзаца
   - Упоминание аспектов
   - Если `has_asc: true`, должна быть фраза "есть контакт с Асцендентом"

3. **Советы:**
   - 1-2 практичных совета под режим (romance/friendship)

4. **Позитивный финал:**
   - Одна фраза без вводных слов

---

## 🐛 Если что-то не работает

### Проблема: "Service unavailable" (503)
**Решение:** Проверьте логи:
```bash
docker-compose logs backend
```

### Проблема: "Connection refused"
**Решение:** Убедитесь, что контейнер запущен:
```bash
docker-compose ps
```

### Проблема: "Invalid model"
**Решение:** Проверьте, что в .env файле правильно указаны:
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`

### Проблема: Ошибки валидации данных
**Решение:** Проверьте формат JSON. Все поля обязательны:
- `mode` должен быть `"romance"` или `"friendship"`
- `gender` должен быть `"male"` или `"female"`
- `type` в аспектах должен быть одним из: `"conjunction"`, `"sextile"`, `"square"`, `"trine"`, `"opposition"`

---

## 🎉 Готово!

Если всё работает, вы увидите интерпретацию совместимости в заданном формате!
