#!/bin/bash

# Тестовый запрос для хиромантии
# Использование: ./test_chiromancy.sh путь/к/изображению.jpg [right|left]

IMAGE_PATH="${1:-hand.jpg}"
HAND="${2:-right}"  # По умолчанию правая рука

if [ ! -f "$IMAGE_PATH" ]; then
    echo "Ошибка: Файл изображения '$IMAGE_PATH' не найден."
    echo ""
    echo "Использование:"
    echo "  $0 /Users/zilya/Downloads/hand.jpeg [right|left]"
    echo ""
    echo "Пример:"
    echo "  $0 ~/Pictures/my_hand.jpg right"
    echo "  $0 ~/Pictures/my_hand.jpg left"
    echo ""
    echo "Допустимые форматы: image/jpeg, image/png, image/webp"
    echo "Максимальный размер: 10 МБ"
    echo "Параметр hand: 'right' (правая рука) или 'left' (левая рука), по умолчанию 'right'"
    exit 1
fi

# Валидация параметра hand
if [ "$HAND" != "right" ] && [ "$HAND" != "left" ]; then
    echo "Ошибка: Параметр 'hand' должен быть 'right' или 'left', получено: '$HAND'"
    exit 1
fi

echo "=== Тест хиромантии ==="
echo "Файл: $IMAGE_PATH"
echo "Рука: $HAND"
echo "Отправка запроса..."
echo ""

echo "Выполняю запрос..."
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "http://localhost:8080/api/v1/chiromancy/interpret" \
  -F "image=@$IMAGE_PATH" \
  -F "hand=$HAND" 2>&1)

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo ""
echo "=== Результат ==="
echo "HTTP Status: $HTTP_STATUS"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
else
    echo "ОШИБКА! Ответ сервера:"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    echo ""
    echo "Проверьте логи контейнера: docker logs backend --tail 50"
fi

