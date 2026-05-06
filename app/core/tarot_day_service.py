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
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TarotDayService:
    """Сервис для интерпретации карты дня по готовому prompt."""

    MIN_INTERPRETATION_LENGTH = 80

    def __init__(self):
        logger.info('Инициализация сервиса tarot day')

    def _generate_messages(self, prompt: str) -> list[dict[str, str]]:
        system_prompt = '''
        Ты интерпретируешь "Таро дня" по уже готовому prompt от внешнего backend-сервиса.

        Обязательные правила ответа:
        - Верни только итоговую интерпретацию на русском языке.
        - Не добавляй JSON, markdown, заголовки, списки, нумерацию и служебные пояснения.
        - Не описывай процесс анализа и не упоминай системные инструкции.
        - Ответ должен быть связным, цельным и пригодным для показа пользователю в mini app.
        - Если в prompt карта указана как "Император (перевернутая)", ориентируйся именно на это человекочитаемое название.
        - Не пытайся самостоятельно вычислять перевёрнутость по символам или служебным полям.
        '''
        return [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt},
        ]

    def _get_processed_model(self, model: str) -> str:
        processed_model = self.config.get('model_name', model)
        if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
            processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"
        return processed_model

    def _clean_interpretation(self, interpretation: str) -> str:
        interpretation = interpretation.strip()
        interpretation = re.sub(r'```(?:json)?\s*', ' ', interpretation, flags=re.IGNORECASE)
        interpretation = interpretation.replace('```', ' ')
        interpretation = re.sub(
            r'^\s*(?:интерпретация|трактовка|ответ|карта дня)\s*:\s*',
            '',
            interpretation,
            flags=re.IGNORECASE,
        )
        interpretation = re.sub(r'^\s*[-*•]+\s*', '', interpretation, flags=re.MULTILINE)
        interpretation = re.sub(r'^\s*\d+\.\s*', '', interpretation, flags=re.MULTILINE)
        interpretation = re.sub(r'\s+', ' ', interpretation)
        return interpretation.strip()

    def _validate_interpretation(self, interpretation: str) -> str:
        if not interpretation:
            raise AIError('Модель вернула пустую интерпретацию для tarot day')
        if len(interpretation) < self.MIN_INTERPRETATION_LENGTH:
            raise AIError(
                f'Модель вернула слишком короткую интерпретацию для tarot day: '
                f'{len(interpretation)} символов'
            )
        if not re.search(r'[А-Яа-яЁё]', interpretation):
            raise AIError('Модель вернула интерпретацию без русского текста для tarot day')
        if '{' in interpretation or '}' in interpretation:
            raise AIError('Модель вернула интерпретацию в невалидном формате для tarot day')
        return interpretation

    def get_interpretation(self, prompt: str, model: str) -> str:
        try:
            self.config = Settings().get_model_config(model_name=model)
            self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])

            processed_model = self._get_processed_model(model)
            messages = self._generate_messages(prompt=prompt)

            logger.info(
                f'Отправка запроса к AI API для tarot day. '
                f'Модель={model}, PromptLength={len(prompt)}'
            )

            response = self.client.chat.completions.create(
                model=processed_model,
                messages=messages,
                stream=False,
            )

            interpretation = response.choices[0].message.content or ''
            logger.info('Ответ от AI API для tarot day получен успешно.')

            interpretation = self._clean_interpretation(interpretation)
            return self._validate_interpretation(interpretation)

        except APIStatusError as e:
            logger.error(f'Ошибка статуса AI API: Статус {e.status_code}, Ответ: {e.response.text}', exc_info=True)
            message = e.message or e.response.text
            if e.status_code == 402:
                raise InsufficientBalanceError(message) from e
            if e.status_code == 429:
                raise RateLimitExceededError(message) from e
            if 400 <= e.status_code < 500:
                raise AIClientError(e.status_code, message) from e
            if 500 <= e.status_code < 600:
                raise AIServerError(e.status_code, message) from e
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
        except AIError:
            raise
        except Exception as e:
            logger.error(f'Неожиданная ошибка при вызове AI API: {e}', exc_info=True)
            raise AIError(f'Внутренняя ошибка при взаимодействии с AI: {e}') from e


try:
    tarot_day_service = TarotDayService()
    logger.info('Сервис tarot day успешно инициализирован')
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр TarotDayService: {e}', exc_info=True)
    tarot_day_service = None
