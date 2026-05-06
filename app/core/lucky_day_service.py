import json
import logging
import re

from openai import APIConnectionError as OpenAIAPIConnectionError, APIError, APIStatusError, OpenAI, RateLimitError

from app.core.config import Settings
from app.core.models import (
    AIError,
    AIClientError,
    AIConnectionError,
    AIServerError,
    InsufficientBalanceError,
    RateLimitExceededError,
    ServiceUnavailableError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LuckyDayService:
    """
    Сервис для анализа запроса пользователя и определения параметров удачного дня.
    """

    def __init__(self):
        """Инициализация сервиса анализа удачного дня."""
        logger.info('Инициализация сервиса анализа удачного дня')

    def _generate_prompt(
        self,
        query_ru: str,
        allowed_tags_en: list[str],
        allowed_score_keys: list[str]
    ) -> tuple[str, str]:
        """
        Генерирует системный и пользовательский промпты для модели.
        
        Args:
            query_ru: Запрос пользователя на русском языке
            allowed_tags_en: Массив допустимых EN-тегов
            allowed_score_keys: Массив допустимых ключей для scores
            
        Returns:
            Кортеж (system_prompt, user_prompt)
        """
        allowed_tags_str = ", ".join(allowed_tags_en)
        allowed_score_keys_str = ", ".join(allowed_score_keys)
        
        system_prompt_template = f'''
        Твоя задача - проанализировать запрос пользователя и определить, какие параметры дня ему подходят для достижения его цели.

        Ты получаешь:
        - `query_ru` — запрос пользователя на русском языке, описывающий, чего он хочет (например, "удачный день для важного разговора")
        - `allowed_tags_en` — массив допустимых EN-тегов, из которых можно выбирать: {allowed_tags_str}
        - `allowed_score_keys` — массив допустимых ключей для scores: {allowed_score_keys_str}

        Твоя задача:
        1. Проанализировать запрос пользователя и понять, что ему нужно
        2. Определить, какие теги дня подходят под его цель (intent_tags) — выбирай ТОЛЬКО из allowed_tags_en
        3. Определить, какие теги нежелательны (avoid_tags) — выбирай ТОЛЬКО из allowed_tags_en
        4. Определить веса параметров дня (weights_scores) — используй ТОЛЬКО ключи из allowed_score_keys, значения в диапазоне [-1..1]
           - Положительное значение означает "хочу больше этого параметра" (например, focus: 0.8 — нужно больше фокуса)
           - Отрицательное значение означает "хочу меньше этого параметра" (например, risk: -0.7 — избегать риска)
        5. Написать короткое описание на русском языке (best_text_ru), объясняющее, почему такой день подходит под запрос

        Требования к ответу:
        - intent_tags: массив строк из allowed_tags_en (обычно 2-6 тегов, может быть пустым)
        - avoid_tags: массив строк из allowed_tags_en (обычно 2-6 тегов, может быть пустым)
        - weights_scores: объект с ключами из allowed_score_keys, значениями number в диапазоне [-1..1]
        - best_text_ru: строка на русском языке, 120-240 символов, естественным языком, без канцелярита

        ВАЖНО:
        - Выбирай intent_tags и avoid_tags ТОЛЬКО из allowed_tags_en
        - Используй ключи weights_scores ТОЛЬКО из allowed_score_keys
        - Значения weights_scores должны быть в диапазоне [-1..1]
        - best_text_ru должен быть естественным, понятным текстом на русском языке
        - Верни ТОЛЬКО валидный JSON без текста вокруг

        Верни ТОЛЬКО валидный JSON строго в формате:
        {{
          "intent_tags": ["<tag>", "<tag>"],
          "avoid_tags": ["<tag>", "<tag>"],
          "weights_scores": {{
            "<key>": <number>
          }},
          "best_text_ru": "<описание на русском языке>"
        }}
        '''

        user_prompt = f'''Проанализируй запрос пользователя и определи параметры удачного дня.

Запрос пользователя: {query_ru}

Допустимые теги: {allowed_tags_str}
Допустимые ключи для scores: {allowed_score_keys_str}

Верни результат в указанном JSON формате.'''

        return system_prompt_template, user_prompt

    def _parse_response(self, response_text: str, allowed_tags_en: list[str], allowed_score_keys: list[str]) -> dict:
        """
        Парсит ответ от модели и извлекает JSON.
        
        Args:
            response_text: Текст ответа от модели
            allowed_tags_en: Массив допустимых EN-тегов для валидации
            allowed_score_keys: Массив допустимых ключей для валидации
            
        Returns:
            Словарь с данными анализа удачного дня
            
        Raises:
            AIError: Если не удалось распарсить ответ
        """
        # Удаляем markdown код блоки, если они есть
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        response_text = response_text.strip()
        
        # Пытаемся найти JSON в ответе
        # Ищем первую открывающую скобку и последнюю закрывающую
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            logger.error(f'Не найден валидный JSON в ответе модели: {response_text[:200]}')
            raise AIError('Модель вернула ответ в неверном формате: отсутствует JSON')
        
        json_text = response_text[start_idx:end_idx + 1]
        
        # Очищаем управляющие символы, которые недопустимы в JSON
        # Оставляем только разрешенные: \n, \r, \t
        # Заменяем остальные на пробелы
        control_chars = ''.join(chr(i) for i in range(32) if chr(i) not in '\n\r\t')
        translation_table = str.maketrans(control_chars, ' ' * len(control_chars))
        json_text = json_text.translate(translation_table)
        
        # Удаляем множественные пробелы, но сохраняем структуру JSON
        json_text = re.sub(r' +', ' ', json_text)
        
        try:
            parsed = json.loads(json_text)
            
            # Валидация структуры
            required_fields = ['intent_tags', 'avoid_tags', 'weights_scores', 'best_text_ru']
            for field in required_fields:
                if field not in parsed:
                    raise AIError(f'В ответе отсутствует поле {field}')
            
            # Валидация типов
            if not isinstance(parsed['intent_tags'], list):
                raise AIError('Поле intent_tags должно быть массивом')
            if not isinstance(parsed['avoid_tags'], list):
                raise AIError('Поле avoid_tags должно быть массивом')
            if not isinstance(parsed['weights_scores'], dict):
                raise AIError('Поле weights_scores должно быть объектом')
            if not isinstance(parsed['best_text_ru'], str):
                raise AIError('Поле best_text_ru должно быть строкой')
            
            # Валидация intent_tags и avoid_tags - должны быть из allowed_tags_en
            for tag in parsed['intent_tags']:
                if tag not in allowed_tags_en:
                    logger.warning(f'Тег {tag} из intent_tags не входит в allowed_tags_en, будет проигнорирован')
            parsed['intent_tags'] = [tag for tag in parsed['intent_tags'] if tag in allowed_tags_en]
            
            for tag in parsed['avoid_tags']:
                if tag not in allowed_tags_en:
                    logger.warning(f'Тег {tag} из avoid_tags не входит в allowed_tags_en, будет проигнорирован')
            parsed['avoid_tags'] = [tag for tag in parsed['avoid_tags'] if tag in allowed_tags_en]
            
            # Валидация weights_scores - ключи должны быть из allowed_score_keys, значения в [-1..1]
            validated_weights = {}
            for key, value in parsed['weights_scores'].items():
                if key not in allowed_score_keys:
                    logger.warning(f'Ключ {key} из weights_scores не входит в allowed_score_keys, будет проигнорирован')
                    continue
                if not isinstance(value, (int, float)):
                    logger.warning(f'Значение для ключа {key} не является числом, будет проигнорировано')
                    continue
                # Ограничиваем значение диапазоном [-1..1]
                validated_value = max(-1.0, min(1.0, float(value)))
                validated_weights[key] = validated_value
            parsed['weights_scores'] = validated_weights
            
            # Валидация длины best_text_ru
            best_text_len = len(parsed['best_text_ru'])
            if best_text_len < 120:
                logger.warning(
                    f'Поле best_text_ru слишком короткое '
                    f'({best_text_len} символов), требуется минимум 120'
                )
            if best_text_len > 240:
                logger.warning(
                    f'Поле best_text_ru слишком длинное '
                    f'({best_text_len} символов), рекомендуется максимум 240'
                )
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f'Ошибка парсинга JSON: {e}, текст: {json_text[:500]}')
            raise AIError(f'Не удалось распарсить JSON из ответа модели: {e}') from e

    def analyze_lucky_day(
        self,
        query_ru: str,
        allowed_tags_en: list[str],
        allowed_score_keys: list[str],
        model: str
    ) -> dict:
        """
        Анализирует запрос пользователя и определяет параметры удачного дня.
        
        Args:
            query_ru: Запрос пользователя на русском языке
            allowed_tags_en: Массив допустимых EN-тегов
            allowed_score_keys: Массив допустимых ключей для scores
            model: Название модели для использования
            
        Returns:
            Словарь с результатом анализа в формате:
            {
                "intent_tags": [...],
                "avoid_tags": [...],
                "weights_scores": {...},
                "best_text_ru": "..."
            }
            
        Raises:
            ServiceUnavailableError: Если сервис недоступен
            AIError: При ошибках взаимодействия с AI API
        """
        try:
            self.config = Settings().get_model_config(model_name=model)
            self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])
            
            system_prompt, user_prompt = self._generate_prompt(
                query_ru=query_ru,
                allowed_tags_en=allowed_tags_en,
                allowed_score_keys=allowed_score_keys
            )
            
            # Обработка специальных моделей Yandex
            processed_model = self.config.get('model_name', model)
            if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
                processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"
            
            logger.info(
                f'Отправка запроса к AI API для анализа удачного дня: '
                f'Запрос={query_ru[:50]}...'
            )
            
            response = self.client.chat.completions.create(
                model=processed_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                stream=False,
            )
            
            response_text = response.choices[0].message.content
            logger.info('Ответ от AI API получен успешно.')
            
            # Парсим ответ в нужный формат
            lucky_day_data = self._parse_response(
                response_text,
                allowed_tags_en=allowed_tags_en,
                allowed_score_keys=allowed_score_keys
            )
            
            logger.info('Анализ удачного дня успешно выполнен')
            return lucky_day_data

        except APIStatusError as e:
            logger.error(f'Ошибка статуса AI API: Статус {e.status_code}, Ответ: {e.response.text}', exc_info=True)
            message = e.message or e.response.text
            if e.status_code == 402:
                raise InsufficientBalanceError(message) from e
            elif e.status_code == 429:
                raise RateLimitExceededError(message) from e
            elif 400 <= e.status_code < 500:
                raise AIClientError(e.status_code, message) from e
            elif 500 <= e.status_code < 600:
                raise AIServerError(e.status_code, message) from e
            else:
                raise AIError(f'Неожиданный статус AI API {e.status_code}: {message}') from e
        except RateLimitError as e:
            logger.error(f'Ошибка лимита запросов AI API: {e}', exc_info=True)
            raise RateLimitExceededError(str(e)) from e
        except OpenAIAPIConnectionError as e:
            logger.error(f'Ошибка соединения с AI API: {e}', exc_info=True)
            raise AIConnectionError(f'Не удалось подключиться к AI API: {e}') from e
        except APIError as e:
            logger.error(f'Общая ошибка AI API: {e}', exc_info=True)
            raise AIError(f'Общая ошибка AI API: {e}') from e
        except Exception as e:
            logger.error(f'Неожиданная ошибка при вызове AI API: {e}', exc_info=True)
            raise AIError(f'Внутренняя ошибка при взаимодействии с AI: {e}') from e


# --- Синглтон Экземпляр Сервиса ---
try:
    lucky_day_service = LuckyDayService()
    logger.info('Сервис анализа удачного дня успешно инициализирован')
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр LuckyDayService: {e}', exc_info=True)
    # Приложение не сможет работать без сервиса. Установим lucky_day_service = None,
    # чтобы эндпоинт мог вернуть 503 и будем проверять в эндпоинте.
    lucky_day_service = None
