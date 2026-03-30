#!/bin/bash

# Тестовый запрос для сонника
echo "=== Тест сонника ==="
curl -X POST "http://localhost:8081/api/v1/sonnik/interpret" \
  -H "Content-Type: application/json" \
  -d '{
    "dream_text": "Мне снилось, что я иду по лесу и нахожу старый замок. В замке были красивые картины и музыка.",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.'

