#!/bin/bash

# Тестовый запрос для гороскопа
echo "=== Тест гороскопа ==="
curl -X POST "http://localhost:8080/api/v1/horoscope/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "day": "2026-01-18",
      "sign": "Овен",
      "day_params_ru": "Эмоции: 0.90, Фокус: -0.20, Общение: 0.70, Импульсивность: 0.40, Конфликтность: 0.30, Риск: 0.20, Энергия: 0.45, Рациональность: -0.20",
      "sign_profile_ru": "Импульсивность: 0.35, Энергия: 0.45, Рациональность: -0.20",
      "allowed_tags_en": ["high_energy","low_energy","high_focus","low_focus","high_emotion","low_emotion","easy_communication","hard_communication","high_impulse","low_impulse","high_rationality","low_rationality","conflict_risk","peaceful_day","high_risk","safe_choice","good_for_talks","good_for_productivity","good_for_decisions","good_for_new_contacts","avoid_hasty_decisions","avoid_conflicts","good_for_changes","need_rest"]
    },
    "model": "Qwen/Qwen3-Next-80B-A3B-Instruct"
  }' | jq '.'

