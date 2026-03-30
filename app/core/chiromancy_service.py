import base64
import logging

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


class ChiromancyService:
    """
    Сервис для интерпретации хиромантии по фото руки с использованием AI.
    """

    # Максимальный размер файла: 10 МБ
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # Допустимые типы изображений
    ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

    def __init__(self):
        """Инициализация сервиса хиромантии."""
        logger.info('Инициализация сервиса хиромантии')

    def _validate_image(self, file_content: bytes, content_type: str) -> None:
        """
        Валидирует изображение по типу и размеру.
        
        Args:
            file_content: Содержимое файла
            content_type: MIME-тип файла
            
        Raises:
            ValueError: Если файл не соответствует требованиям
        """
        # Проверка типа файла
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f'Недопустимый тип файла: {content_type}. '
                f'Разрешены только: {", ".join(self.ALLOWED_CONTENT_TYPES)}'
            )
        
        # Проверка размера файла
        file_size = len(file_content)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f'Размер файла ({file_size} байт) превышает максимально допустимый ({self.MAX_FILE_SIZE} байт)'
            )
        
        if file_size == 0:
            raise ValueError('Файл пуст')

    def _convert_to_data_url(self, file_content: bytes, content_type: str) -> str:
        """
        Конвертирует изображение в data URL формат.
        
        Args:
            file_content: Содержимое файла
            content_type: MIME-тип файла
            
        Returns:
            Data URL строка в формате data:<mime>;base64,<...>
        """
        base64_content = base64.b64encode(file_content).decode('utf-8')
        return f'data:{content_type};base64,{base64_content}'

    def _generate_prompt(self, hand: str = 'right') -> tuple[str, str]:
        """
        Генерирует системный и пользовательский промпты для модели.
        
        Args:
            hand: Рука пользователя - 'right' (правая) или 'left' (левая)
        
        Returns:
            Кортеж (system_prompt, user_prompt)
        """
        hand_text = 'правша' if hand == 'right' else 'левша'
        hand_description = 'Левая рука — врождённые качества и потенциал; правая рука — то, что реализовано и проявляется сейчас.' if hand == 'right' else 'Правая рука — врождённые качества и потенциал; левая рука — то, что реализовано и проявляется сейчас.'
        
        system_prompt_template = f'''
        Ты — опытный хиромант. Анализируй только то, что реально видно на фото ладони. Если какой-то признак читается плохо — скажи об этом одной короткой фразой и не делай выводов по нему.
        
        Входные данные: пользователь — {hand_text} — это достоверно.
        Определи по фото, какая рука изображена:
        Если большой палец слева на изображении ладони — это левая рука, если большой палец справа — это правая рука.
        Если по фото нельзя уверенно определить руку (ракурс/зеркальность/обрезано), продолжай без привязки к “врождённое/проявленное”.

        ВАЖНО: Запрещено объяснять в ответе, как определена рука. Нельзя упоминать “большой палец слева/справа”, “на фото видно”, “это левая/правая рука”.

        Правило смысла руки (обязательно учитывай в выводах):
        {hand_description}
        Если анализируется врождённая рука — говори про склонности и потенциал.
        Если анализируется проявленная рука — говори про привычки и то, как человек действует сейчас.
        
        Структура ответа (абзацы, без заголовков, без двоеточий):
        Линия жизни;
        Линия головы;
        Линия сердца;
        Линия судьбы (если различима);
        Другие линии (только если хоть немного различимы; иначе одна короткая фраза);
        В финальном абзаце скажи две(или одну) сильные стороны (по смыслу линий), а затем закончи одним выводом — без вводных слов и без меток.  В финале можно использовать только те качества, которые уже были названы в предыдущих абзацах. Финальный абзац должен быть, без высоких слов, но как связанный красивый текст.
        
        Справка по линиям (не путай):
        Линия сердца — верхняя поперечная линия под пальцами, обычно от края под мизинцем к области под указательным/средним.
        Линия головы — ниже линии сердца, часто от зоны между большим и указательным к внешнему краю ладони.
        Линия жизни — дуга вокруг холма Венеры, от зоны между большим и указательным вниз к запястью.
        Линия судьбы — вертикальная линия ближе к центру ладони от запястья вверх (может быть слабой/прерывистой).

        Правила содержания для каждого абзаца про линию:
        Сначала 2–3 видимых признака (начало/направление/длина/чёткость/глубина/волнистость/разрывы/ветви/пересечения) — только то, что читается.
        Затем трактовка “в рамках хиромантии” — мягко, без категоричности.
        Затем “что делать”: один дельный совет-навык на годы (про разговоры, границы, решения, фокус, отношения, дисциплину). Никаких “подыши 2–3 минуты”, медитаций и микрозадач по таймеру.

        Стиль:
        Русский язык, обращение на “ты”.
        Пиши красиво и гладко, как консультант: живой язык, но без канцелярита и без “книжной эзотерики”.
        Избегай повторов “это говорит”, “это указывает”, “совет:”, “ты можешь” — вариируй формулировки.
        Разрешены 1–2 коротких жизненных примера на весь текст (не в каждом абзаце), чтобы было узнаваемо и “по делу”.
        Запрещены темы: здоровье, болезни, диагнозы, медицина, длительность жизни.
        Только plain text, без списков, без Markdown.
        Не используй слово «совет»,'Принцип на годы:'. Формулируй рекомендации как мягкое предложение

        Язык и звучание (обязательно):
        Пиши естественно, как живой русский: “ясно думаешь”, а не “думаешь ясно”; “умеешь держаться”, а не “умеешь сохранять”.
        Избегай канцелярита и общих слов: “выйти из положения”, “внешние обстоятельства”, “нестабильное окружение”, “внутреннее напряжение”.
        Если даёшь пример, он должен быть конкретным и понятным без контекста. Не используй примеры про “незнакомый город/паника/положение”. Лучше примеры из реальной жизни: спор на работе, разговор с партнёром, выбор между задачами, усталость и дедлайны.
        Пиши меньше вводных “это говорит о том, что…”, больше простых связок.

        Объём: строго 250–300 слов.
        '''

        user_prompt = f'''Проанализируй это фото руки и дай подробную интерпретацию по хиромантии. Опиши все видимые линии, их особенности и значение. Учитывай, что это {hand_text}.'''

        return system_prompt_template, user_prompt

    def get_interpretation(
        self,
        image_content: bytes,
        content_type: str,
        hand: str,
        model: str
    ) -> str:
        """
        Получает интерпретацию хиромантии по фото руки от модели ИИ.
        
        Args:
            image_content: Содержимое изображения
            content_type: MIME-тип изображения
            hand: Рука пользователя - 'right' (правая) или 'left' (левая)
            model: Название модели для использования
            
        Returns:
            Интерпретация хиромантии
            
        Raises:
            ValueError: Если изображение не прошло валидацию
            ServiceUnavailableError: Если сервис недоступен
            AIError: При ошибках взаимодействия с AI API
        """
        try:
            # Валидация изображения
            self._validate_image(image_content, content_type)
            
            # Конвертация в data URL
            image_data_url = self._convert_to_data_url(image_content, content_type)
            
            # Получение конфигурации модели
            self.config = Settings().get_model_config(model_name=model)
            self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])
            
            # Генерация промптов
            system_prompt, user_prompt = self._generate_prompt(hand=hand)
            
            # Обработка специальных моделей Yandex
            processed_model = model
            if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
                processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"
            
            logger.info(
                f'Отправка запроса к AI API для интерпретации хиромантии: '
                f'Размер изображения={len(image_content)} байт, Тип={content_type}, Рука={hand}, Модель={model}'
            )
            
            # Формирование сообщения с изображением
            # Используем формат OpenAI для мультимодальных запросов
            messages = [
                {'role': 'system', 'content': system_prompt},
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': user_prompt
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': image_data_url
                            }
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=processed_model,
                messages=messages,
                stream=False,
            )
            
            interpretation = response.choices[0].message.content
            logger.info('Ответ от AI API получен успешно.')
            
            return interpretation.strip() if interpretation else '(Пустая интерпретация от AI)'

        except ValueError as e:
            logger.error(f'Ошибка валидации изображения: {e}', exc_info=True)
            raise
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
    chiromancy_service = ChiromancyService()
    logger.info('Сервис хиромантии успешно инициализирован')
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр ChiromancyService: {e}', exc_info=True)
    chiromancy_service = None

