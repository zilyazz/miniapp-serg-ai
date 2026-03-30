#!/bin/bash

# Тестовый запрос для совместимости
echo "=== Тест совместимости ==="
curl -X POST "http://localhost:8081/api/v1/compatibility/analyze" \
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
        },
        {
          "a": "Венера",
          "b": "Марс",
          "type": "sextile",
          "weight": 8
        }
      ],
      "stats": {
        "harmonious_count": 12,
        "challenging_count": 3,
        "has_asc": true
      }
    },
    "premium": false,
    "model": "Qwen/Qwen3-Next-80B-A3B-Instruct"
  }' | jq '.'

