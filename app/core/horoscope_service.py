import json
import logging
import re
import string

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


class HoroscopeService:
    """
    Сервис для генерации гороскопа по знаку зодиака и дате.
    Гороскоп одинаковый для всех пользователей одного знака на одну дату.
    """

    def __init__(self):
        """Инициализация сервиса гороскопа."""
        logger.info('Инициализация сервиса гороскопа')

    def _generate_prompt(
        self,
        day: str,
        sign: str,
        day_params_ru: str,
        sign_profile_ru: str,
        allowed_tags_en: list[str]
    ) -> tuple[str, str]:
        """
        Генерирует системный и пользовательский промпты для модели.
        
        Args:
            day: Дата в формате YYYY-MM-DD
            sign: Русское название знака зодиака
            day_params_ru: Параметры дня на русском языке
            sign_profile_ru: Параметры профиля знака на русском языке
            allowed_tags_en: Массив допустимых EN-тегов
            
        Returns:
            Кортеж (system_prompt, user_prompt)
        """
        system_prompt_template = '''
        Твоя задача - создать ежедневный гороскоп для указанного знака зодиака на указанную дату.  
        Гороскоп должен быть одинаковым для всех людей данного знака на эту дату.

        Ты получаешь входные данные:

        - `day` — дата (YYYY-MM-DD)
            
        - `sign` — знак зодиака (русское название)
            
        - `day_params_ru` — параметры фона дня на русском языке (числа от -1 до 1)
            
        - `sign_profile_ru` — профиль знака на русском языке (может быть пустым). Это НЕ прогноз, а "характерная манера реагировать" данного знака. Используй профиль как фильтр: один и тот же фон дня разные знаки проживают по-разному.
            
        - `allowed_tags_en` — массив допустимых EN-тегов, из которых можно выбирать
            

        Как использовать `day_params_ru` и `sign_profile_ru`

        - `day_params_ru` задаёт обстоятельства дня: темп, коммуникации, риск, напряжение и т.д.
            
        - `sign_profile_ru` задаёт "типичный стиль" знака: например, более импульсивный знак сильнее реагирует на высокий `impulse` дня, а более рациональный — легче держит баланс при низкой `rationality`.
            
        - Если `sign_profile_ru` пустой, опирайся только на `day_params_ru`.
            
        - Не пересказывай параметры как "цифры", но делай так, чтобы текст логично вытекал из них.

        Пояснение параметров scores:

        - energy - уровень энергии и запаса сил
            
        - emotion - интенсивность эмоций и чувств
            
        - impulse - склонность к импульсивным действиям
            
        - communication - лёгкость и качество общения
            
        - focus - способность концентрироваться
            
        - rationality - холодная голова и взвешенность решений
            
        - conflict - риск споров и напряжения
            
        - risk - вероятность ошибок и неудачных шагов
            

        ВАЖНОЕ ПРАВИЛО СТИЛЯ:

        - Гороскоп должен восприниматься как вероятностное описание, а не как точное обещание событий.
        - Допускается использование модальных конструкций ("возможны", "вероятны", "не исключено", "может"), но не требуется использовать их в каждом предложении.
        - Допускается использование слова "будет", если оно не звучит как категоричное обещание и используется в контексте вероятности.
        - Пиши так, как если бы текст готовил редактор популярного астрологического сайта, а не аналитик или психолог.
        - Предложения должны быть простыми и легко читаться.

        Структура гороскопа.

        general_public:

        - Один абзац
            
        - Не короче 110 символов
            
        - Описывает общий фон дня для данного знака
            
        - Утренний тон (читают утром перед днём)
            
        - Первое предложение описывает внешнюю ситуацию дня (встречи, разговоры, темп, обстоятельства), в будущем времени и с модальностью
            
        - Пиши естественным русским, как в популярных гороскопах (радио/сайты), без канцелярита
            
        - Запрещены фразы: "в течение дня", "на протяжении дня", "часто складываются ситуации"
            
        - В конце добавь одно короткое завершающее предложение-ориентир, тоже с модальностью (например: "Лучше всего сегодня может получаться ...")
        - Предложения должны быть короткими или средней длины.
        - Избегай сложных вложенных конструкций.
            

        general_premium:

        - Логическое продолжение general_public
            
        - Минимум два абзаца, разделённые пустой строкой (\n\n)
            
        - Не короче 180 символов
            
        - Раскрывает детали, нюансы и возможные сценарии дня
            
        - Не повторяет general_public
            
        - Не начинает новый независимый текст
            
        - Каждый абзац 2-3 предложения
            
        - Стиль классического ежедневного гороскопа
            
        - Больше ситуаций и обстоятельств, меньше психологии
            
        - Избегай советов в форме действий и терапевтического тона
        - Текст должен напоминать журнальный гороскоп, а не рассуждение или анализ.
            

        Запрещено:

        - Разделы "любовь", "работа", "деньги"
            
        - Заголовки, списки и маркировка
            
        - Упоминать оплату, премиум или доступ
            
        - Любой текст вне JSON
            
        - Советы в форме действий ("дышать", "сделать паузу", "переключиться", "прислушаться")
            
        - Формулировки с обещанием эффекта ("это поможет", "это снизит", "это позволит")
            

        Теги и оценки:

        - tags - массив EN-тегов
            
        - Выбирай ТОЛЬКО из allowed_tags_en
            
        - Обычно используй от 3 до 6 тегов
            
        - Теги должны соответствовать тексту и параметрам дня
            

        scores:

        - Объект числовых значений от -1 до 1
            
        - Используй ТОЛЬКО ключи: energy, emotion, impulse, communication, focus, rationality, conflict, risk
            
        - Значения scores должны соответствовать тексту и тегам
            

        Верни ТОЛЬКО валидный JSON строго в формате:

        {  
        "content_ru": {  
        "general_public": "<публичная часть>",  
        "general_premium": "<премиум-продолжение>"  
        },  
        "tags": ["<tag>", "<tag>"],  
        "scores": {  
        "<key>": <number>  
        }  
        }

        Требования:

        - Весь текст строго на русском языке
            
        - Абзацы разделяй пустой строкой (\n\n)
            
        - JSON должен быть валидным
            
        - Никакого текста вне JSON
        '''

        # Формируем пользовательский промпт
        sign_profile_text = f"\nПрофиль знака: {sign_profile_ru}" if sign_profile_ru.strip() else ""
        allowed_tags_str = ", ".join(allowed_tags_en)
        
        user_prompt = f'''Составь гороскоп для знака зодиака "{sign}" на дату {day}.

Параметры дня: {day_params_ru}{sign_profile_text}

Допустимые теги: {allowed_tags_str}

Верни гороскоп в указанном JSON формате.'''

        return system_prompt_template, user_prompt

    def _parse_response(self, response_text: str) -> dict:
        """
        Парсит ответ от модели и извлекает JSON.
        
        Args:
            response_text: Текст ответа от модели
            
        Returns:
            Словарь с данными гороскопа
            
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
        # Создаем таблицу переводов: все управляющие символы кроме разрешенных заменяем на пробелы
        control_chars = ''.join(chr(i) for i in range(32) if chr(i) not in '\n\r\t')
        translation_table = str.maketrans(control_chars, ' ' * len(control_chars))
        json_text = json_text.translate(translation_table)
        
        # Удаляем множественные пробелы, но сохраняем структуру JSON
        json_text = re.sub(r' +', ' ', json_text)
        
        try:
            parsed = json.loads(json_text)
            
            # Валидация структуры
            if 'content_ru' not in parsed:
                raise AIError('В ответе отсутствует поле content_ru')
            
            content_ru = parsed['content_ru']
            required_fields = ['general_public', 'general_premium']
            for field in required_fields:
                if field not in content_ru:
                    raise AIError(f'В ответе отсутствует поле content_ru.{field}')
            
            # Минимальные проверки длины (не падаем, только предупреждаем — модель может слегка ошибиться)
            if len(content_ru.get('general_public', '')) < 110:
                logger.warning(
                    f'Поле general_public слишком короткое '
                    f'({len(content_ru.get("general_public", ""))} символов), требуется минимум 110'
                )
            if len(content_ru.get('general_premium', '')) < 180:
                logger.warning(
                    f'Поле general_premium слишком короткое '
                    f'({len(content_ru.get("general_premium", ""))} символов), требуется минимум 180'
                )
            
            # Убеждаемся, что tags и scores присутствуют (могут быть пустыми)
            if 'tags' not in parsed:
                parsed['tags'] = []
            if 'scores' not in parsed:
                parsed['scores'] = {}
            
            # Проверяем типы
            if not isinstance(parsed['tags'], list):
                parsed['tags'] = []
            if not isinstance(parsed['scores'], dict):
                parsed['scores'] = {}
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f'Ошибка парсинга JSON: {e}, текст: {json_text[:500]}')
            raise AIError(f'Не удалось распарсить JSON из ответа модели: {e}') from e

    def get_horoscope(
        self,
        day: str,
        sign: str,
        day_params_ru: str,
        sign_profile_ru: str,
        allowed_tags_en: list[str],
        model: str
    ) -> dict:
        """
        Получает гороскоп от модели ИИ.
        
        Args:
            day: Дата в формате YYYY-MM-DD
            sign: Русское название знака зодиака
            day_params_ru: Параметры дня на русском языке
            sign_profile_ru: Параметры профиля знака на русском языке
            allowed_tags_en: Массив допустимых EN-тегов
            model: Название модели для использования
            
        Returns:
            Словарь с гороскопом в формате:
            {
                "content_ru": {
                    "general_public": "...",
                    "general_premium": "..."
                },
                "tags": [...],
                "scores": {...}
            }
            
        Raises:
            ServiceUnavailableError: Если сервис недоступен
            AIError: При ошибках взаимодействия с AI API
        """
        try:
            self.config = Settings().get_model_config(model_name=model)
            self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])
            
            system_prompt, user_prompt = self._generate_prompt(
                day=day,
                sign=sign,
                day_params_ru=day_params_ru,
                sign_profile_ru=sign_profile_ru,
                allowed_tags_en=allowed_tags_en
            )
            
            # Обработка специальных моделей Yandex
            processed_model = model
            if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
                processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"
            
            logger.info(
                f'Отправка запроса к AI API для генерации гороскопа: '
                f'Знак={sign}, Дата={day}'
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
            horoscope_data = self._parse_response(response_text)
            
            logger.info(f'Гороскоп успешно сгенерирован для знака {sign} на дату {day}')
            return horoscope_data

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
    horoscope_service = HoroscopeService()
    logger.info('Сервис гороскопа успешно инициализирован')
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр HoroscopeService: {e}', exc_info=True)
    # Приложение не сможет работать без сервиса. Установим horoscope_service = None,
    # чтобы эндпоинт мог вернуть 503 и будем проверять в эндпоинте.
    horoscope_service = None

