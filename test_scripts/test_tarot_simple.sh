#!/bin/bash

# Упрощенный тестовый запрос (без jq)
curl -X POST "http://localhost:8081/api/v1/tarot/interpret" \
  -H "Content-Type: application/json" \
  -d '{
    "tarot": ["Маг", "Императрица", "Звезда"],
    "question": "Что меня ждет в отношениях?",
    "theme": "любовь",
    "type": "classic",
    "premium": true,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }'

