#!/bin/bash

# Скрипт для тестирования всех эндпоинтов
echo "=========================================="
echo "Тестирование всех эндпоинтов API"
echo "=========================================="
echo ""

# Тест 1: Расклады рун
echo "1. Тест расклада рун (Divination)"
echo "-----------------------------------"
curl -s -X POST "http://localhost:8081/api/v1/divination/encode" \
  -H "Content-Type: application/json" \
  -d '{
    "runes": ["Феху", "Райдо", "Хагалаз"],
    "theme": "любовь",
    "type": "classic",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.' || echo "ОШИБКА: Расклады рун не работают"
echo ""
echo ""

# Тест 2: Сонник
echo "2. Тест сонника (Sonnik)"
echo "-----------------------------------"
curl -s -X POST "http://localhost:8081/api/v1/sonnik/interpret" \
  -H "Content-Type: application/json" \
  -d '{
    "dream_text": "Мне снилось, что я иду по лесу и нахожу старый замок.",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.' || echo "ОШИБКА: Сонник не работает"
echo ""
echo ""

# Тест 3: Совместимость
echo "3. Тест совместимости (Compatibility)"
echo "-----------------------------------"
curl -s -X POST "http://localhost:8081/api/v1/compatibility/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "mode": "romance",
      "score": 85,
      "label": "Отличная совместимость",
      "person_a": {
        "name": "Анна",
        "gender": "female",
        "element": "Огонь"
      },
      "person_b": {
        "name": "Иван",
        "gender": "male",
        "element": "Воздух"
      },
      "top_aspects": [
        {
          "a": "Солнце",
          "b": "Луна",
          "type": "trine",
          "weight": 10
        }
      ],
      "stats": {
        "harmonious_count": 12,
        "challenging_count": 3,
        "has_asc": true
      }
    },
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.' || echo "ОШИБКА: Совместимость не работает"
echo ""
echo ""

# Тест 4: Таро (основной расклад)
echo "4. Тест Таро - основной расклад (Tarot)"
echo "-----------------------------------"
curl -s -X POST "http://localhost:8081/api/v1/tarot/interpret" \
  -H "Content-Type: application/json" \
  -d '{
    "tarot": ["Маг", "Императрица", "Звезда"],
    "question": "Что меня ждет в отношениях?",
    "type": "classic",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.' || echo "ОШИБКА: Таро (основной) не работает"
echo ""
echo ""

# Тест 5: Таро (продолжение)
echo "5. Тест Таро - продолжение расклада (Tarot Followup)"
echo "-----------------------------------"
curl -s -X POST "http://localhost:8081/api/v1/tarot/followup" \
  -H "Content-Type: application/json" \
  -d '{
    "history": [
      {
        "question": "Стоит ли покупать машину",
        "cards": ["Маг", "Императрица"],
        "interpretation": "Расклад показывает позитивные перспективы покупки.",
        "kind": "main",
        "seq": 0
      }
    ],
    "new_card": "Рыцарь Кубков*",
    "question": "Как перестать ее покупать?",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.' || echo "ОШИБКА: Таро (продолжение) не работает"
echo ""
echo ""

echo "=========================================="
echo "Тестирование завершено!"
echo "=========================================="

