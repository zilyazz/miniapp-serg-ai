# Примеры использования API для Таро

## 1. Основной расклад Таро

### Endpoint
`POST /api/v1/tarot/interpret`

### JavaScript/TypeScript пример:

```javascript
const payload = {
  tarot: ["Маг", "Императрица", "Звезда"],  // Массив карт
  question: "Что меня ждет в отношениях?",   // Вопрос пользователя
  type: "classic",                           // Тип расклада: "classic", "pyramid", "cross"
  premium: false,                            // Флаг премиум-подписки
  model: 'meta-llama/Llama-4-Scout-17B-16E-Instruct',
};

const response = await axios.post('http://localhost:8081/api/v1/tarot/interpret', payload);
const interpretation = response.data.interpretation;
```

### Важные моменты:
- **Без `theme`** - тема расклада больше не используется
- `tarot` - массив строк с названиями карт
- `type` - тип расклада влияет на описание позиций

---

## 2. Продолжение расклада Таро

### Endpoint
`POST /api/v1/tarot/followup`

### JavaScript/TypeScript пример:

```javascript
// Формируем историю раскладов
const history = [
  {
    question: "Стоит ли покупать машину",
    cards: ["Маг", "Императрица", "Звезда"],  // Массив карт для основного расклада
    interpretation: "Расклад показывает позитивные перспективы...",  // Текст интерпретации
    kind: "main",                              // 'main' для основного расклада
    seq: 0                                     // Порядковый номер: 0 для основного
  },
  // Если есть предыдущие продолжения, добавляем их:
  // {
  //   question: "Ну а как перестать ее покупать то",
  //   cards: ["Маг"],                          // Для продолжения всегда ОДНА карта
  //   interpretation: "Текст интерпретации первого продолжения...",
  //   kind: "followup",                        // 'followup' для продолжений
  //   seq: 1                                   // Порядковый номер: 1, 2, 3...
  // }
];

const payload = {
  history: history,                            // Массив истории (обязательно должен быть хотя бы основной расклад)
  new_card: "Рыцарь Кубков*",                // НОВАЯ карта для продолжения (ОДНА карта)
  question: "Как перестать ее покупать?",     // НОВЫЙ вопрос для продолжения
  premium: false,
  model: 'meta-llama/Llama-4-Scout-17B-16E-Instruct',
};

const response = await axios.post('http://localhost:8081/api/v1/tarot/followup', payload);
const interpretation = response.data.interpretation;
```

### Важные моменты:
- `history` - **обязательно должен содержать хотя бы основной расклад** (`kind: "main", seq: 0`)
- `history` должен быть отсортирован по `seq` (0, 1, 2, ...)
- `new_card` - **всегда одна карта** (строка), может быть перевернутой (с `*`)
- Для основного расклада в `history`: `cards` - массив из нескольких карт
- Для продолжений в `history`: `cards` - массив из одной карты

---

## 3. Пример формирования истории на клиенте

```javascript
// После получения основного расклада
let tarotHistory = [
  {
    question: mainQuestion,
    cards: mainCards,              // ["Маг", "Императрица", "Звезда"]
    interpretation: mainInterpretation,
    kind: "main",
    seq: 0
  }
];

// При первом продолжении
const firstFollowup = {
  history: tarotHistory,           // Только основной расклад
  new_card: firstFollowupCard,     // Одна карта
  question: firstFollowupQuestion,
  premium: false,
  model: 'meta-llama/Llama-4-Scout-17B-16E-Instruct',
};

const firstResponse = await axios.post('/api/v1/tarot/followup', firstFollowup);

// Обновляем историю после получения первого продолжения
tarotHistory.push({
  question: firstFollowupQuestion,
  cards: [firstFollowupCard],      // Массив из одной карты
  interpretation: firstResponse.data.interpretation,
  kind: "followup",
  seq: 1
});

// При втором продолжении (если нужно)
const secondFollowup = {
  history: tarotHistory,           // Теперь включает основной + первое продолжение
  new_card: secondFollowupCard,
  question: secondFollowupQuestion,
  premium: false,
  model: 'meta-llama/Llama-4-Scout-17B-16E-Instruct',
};

const secondResponse = await axios.post('/api/v1/tarot/followup', secondFollowup);
```

---

## 4. Обработка перевернутых карт

Перевернутые карты обозначаются символом `*` в конце названия:

```javascript
// Прямая карта
const card = "Маг";

// Перевернутая карта
const reversedCard = "Маг*";
const reversedCard2 = "Рыцарь Кубков*";
```

API автоматически обработает такие карты и добавит пометку "(перевернутая)" в промпт.

---

## 5. Типы раскладов

Поддерживаемые типы:
- `"classic"` - классический расклад на 3 карты
- `"pyramid"` - пирамида (7 карт)
- `"cross"` - крест (6 карт)

Каждый тип имеет свое описание позиций, которое учитывается в интерпретации.

---

# Примеры использования API для Хиромантии

## Хиромантия по фото руки

### Endpoint
`POST /api/v1/chiromancy/interpret`

### Важные моменты:
- **Файл изображения** - обязательное поле `image`
- **Тип руки** - обязательное поле `hand`: `'right'` (правая) или `'left'` (левая)
- Поддерживаемые форматы: `image/jpeg`, `image/png`, `image/webp`
- Максимальный размер файла: 10 МБ
- Модель используется по умолчанию: `meta-llama/Llama-4-Scout-17B-16E-Instruct`

---

### 1. JavaScript/TypeScript (с использованием FormData)

```javascript
// В браузере или Node.js (с поддержкой FormData)
const formData = new FormData();
formData.append('image', imageFile); // imageFile - это File объект из input[type="file"] или Blob
formData.append('hand', 'right'); // 'right' для правой руки, 'left' для левой

const response = await fetch('http://localhost:8080/api/v1/chiromancy/interpret', {
  method: 'POST',
  body: formData
});

const data = await response.json();
const interpretation = data.interpretation;
console.log(interpretation);
```

### Пример с input файлом в браузере:

```javascript
// HTML: <input type="file" id="handImage" accept="image/jpeg,image/png,image/webp" />
const fileInput = document.getElementById('handImage');

fileInput.addEventListener('change', async (event) => {
  const imageFile = event.target.files[0];
  
  if (!imageFile) return;
  
  const formData = new FormData();
  formData.append('image', imageFile);
  
  try {
    const response = await fetch('http://localhost:8080/api/v1/chiromancy/interpret', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Интерпретация:', data.interpretation);
  } catch (error) {
    console.error('Ошибка:', error);
  }
});
```

---

### 2. Node.js (с использованием FormData и fetch или axios)

#### С использованием FormData и fetch (встроенные в Node.js 18+):

```javascript
import FormData from 'form-data';
import fs from 'fs';

async function interpretChiromancy(imagePath, hand = 'right') {
  const formData = new FormData();
  const imageStream = fs.createReadStream(imagePath);
  
  formData.append('image', imageStream);
  formData.append('hand', hand); // 'right' или 'left'
  
  const response = await fetch('http://localhost:8080/api/v1/chiromancy/interpret', {
    method: 'POST',
    body: formData,
    headers: formData.getHeaders() // Важно для правильной установки Content-Type с boundary
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }
  
  const data = await response.json();
  return data.interpretation;
}

// Использование
interpretChiromancy('/path/to/hand.jpg')
  .then(interpretation => console.log(interpretation))
  .catch(error => console.error('Ошибка:', error));
```

#### С использованием axios (требуется установка: npm install axios form-data):

```javascript
import axios from 'axios';
import FormData from 'form-data';
import fs from 'fs';

async function interpretChiromancy(imagePath, hand = 'right') {
  const formData = new FormData();
  const imageStream = fs.createReadStream(imagePath);
  
  formData.append('image', imageStream);
  formData.append('hand', hand); // 'right' или 'left'
  
  try {
    const response = await axios.post(
      'http://localhost:8080/api/v1/chiromancy/interpret',
      formData,
      {
        headers: {
          ...formData.getHeaders(),
        },
        maxContentLength: Infinity,
        maxBodyLength: Infinity,
      }
    );
    
    return response.data.interpretation;
  } catch (error) {
    if (error.response) {
      // Сервер ответил с кодом ошибки
      throw new Error(error.response.data.detail || `HTTP error! status: ${error.response.status}`);
    } else if (error.request) {
      // Запрос был отправлен, но ответа не получено
      throw new Error('Нет ответа от сервера');
    } else {
      // Ошибка при настройке запроса
      throw error;
    }
  }
}

// Использование
interpretChiromancy('/path/to/hand.jpg')
  .then(interpretation => console.log(interpretation))
  .catch(error => console.error('Ошибка:', error));
```

#### С использованием Buffer (если файл уже в памяти):

```javascript
import FormData from 'form-data';
import fs from 'fs/promises';
import path from 'path';

async function interpretChiromancy(imagePath, hand = 'right') {
  const imageBuffer = await fs.readFile(imagePath);
  const formData = new FormData();
  
  formData.append('image', imageBuffer, {
    filename: path.basename(imagePath),
    contentType: 'image/jpeg', // или image/png, image/webp
  });
  formData.append('hand', hand); // 'right' или 'left'
  
  const response = await fetch('http://localhost:8080/api/v1/chiromancy/interpret', {
    method: 'POST',
    body: formData,
    headers: formData.getHeaders()
  });
  
  const data = await response.json();
  return data.interpretation;
}
```

#### Пример Express.js endpoint, который проксирует запрос:

```javascript
import express from 'express';
import multer from 'multer'; // npm install multer
import FormData from 'form-data';
import axios from 'axios';

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.post('/api/chiromancy-proxy', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'Файл не предоставлен' });
    }
    
    const formData = new FormData();
    formData.append('image', req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype,
    });
    // Получаем hand из тела запроса или query параметра
    const hand = req.body.hand || req.query.hand || 'right';
    formData.append('hand', hand);
    
    const response = await axios.post(
      'http://localhost:8080/api/v1/chiromancy/interpret',
      formData,
      {
        headers: formData.getHeaders(),
      }
    );
    
    res.json(response.data);
  } catch (error) {
    console.error('Ошибка:', error);
    res.status(500).json({ 
      error: error.response?.data?.detail || 'Внутренняя ошибка сервера' 
    });
  }
});

app.listen(3000, () => {
  console.log('Сервер запущен на порту 3000');
});
```

#### Использование в TypeScript:

```typescript
import FormData from 'form-data';
import fs from 'fs';
import path from 'path';

interface ChiromancyResponse {
  interpretation: string;
}

async function interpretChiromancy(imagePath: string, hand: 'right' | 'left' = 'right'): Promise<string> {
  const formData = new FormData();
  const imageStream = fs.createReadStream(imagePath);
  
  formData.append('image', imageStream);
  formData.append('hand', hand);
  
  const response = await fetch('http://localhost:8080/api/v1/chiromancy/interpret', {
    method: 'POST',
    body: formData as any,
    headers: formData.getHeaders() as any,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }
  
  const data: ChiromancyResponse = await response.json();
  return data.interpretation;
}

// Использование
interpretChiromancy('/path/to/hand.jpg')
  .then(interpretation => console.log(interpretation))
  .catch(error => console.error('Ошибка:', error));
```

**Установка зависимостей:**

```bash
# Если используете FormData
npm install form-data

# Если используете axios
npm install axios form-data

# Если используете multer для Express
npm install multer @types/multer
```

---

### 3. Axios (браузерный JavaScript)

```javascript
import axios from 'axios';

async function interpretChiromancy(imageFile, hand = 'right') {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('hand', hand); // 'right' или 'left'
  
  try {
    const response = await axios.post(
      'http://localhost:8080/api/v1/chiromancy/interpret',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    
    return response.data.interpretation;
  } catch (error) {
    console.error('Ошибка при отправке запроса:', error);
    throw error;
  }
}

// Использование
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (file) {
    const interpretation = await interpretChiromancy(file);
    console.log(interpretation);
  }
});
```

---

### 4. Ответ API

#### Успешный ответ (200 OK):

```json
{
  "interpretation": "На предоставленной фотографии ладони руки видны основные линии... (детальная интерпретация на русском языке)"
}
```

#### Ошибки:

- **400 Bad Request** - неверный формат файла, размер превышает 10 МБ, или неверное значение параметра `hand` (должно быть 'right' или 'left')
- **502 Bad Gateway** - ошибка на стороне AI API
- **503 Service Unavailable** - сервис временно недоступен

Пример ошибки:

```json
{
  "detail": "Недопустимый тип файла: image/gif. Разрешены только: image/jpeg, image/png, image/webp"
}
```

---

### 5. Обработка ошибок (JavaScript/Node.js)

```javascript
async function interpretChiromancyWithErrorHandling(imageFile, hand = 'right') {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('hand', hand); // 'right' или 'left'
  
  try {
    const response = await fetch('http://localhost:8080/api/v1/chiromancy/interpret', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.interpretation;
    
  } catch (error) {
    if (error.message.includes('HTTP error')) {
      console.error('Ошибка сервера:', error.message);
    } else {
      console.error('Ошибка сети:', error);
    }
    throw error;
  }
}
```



