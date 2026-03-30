#!/bin/bash

# Тестовый запрос с английскими картами (если проблема с кириллицей)
curl -X POST "http://localhost:8081/api/v1/tarot/interpret" \
  -H "Content-Type: application/json" \
  -d '{
    "tarot": ["The Magician", "The Empress", "The Star"],
    "question": "What awaits me in relationships?",
    "theme": "love",
    "type": "classic",
    "premium": false,
    "model": "meta-llama/Llama-4-Scout-17B-16E-Instruct"
  }'

