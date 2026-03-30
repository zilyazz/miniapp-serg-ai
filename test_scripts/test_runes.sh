#!/bin/bash

# Тестовый запрос для расклада рун
echo "=== Тест расклада рун ==="
curl -X POST "http://localhost:8081/api/v1/divination/encode" \
  -H "Content-Type: application/json" \
  -d '{
    "runes": ["Феху", "Райдо", "Хагалаз"],
    "theme": "любовь",
    "type": "classic",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }' | jq '.'

