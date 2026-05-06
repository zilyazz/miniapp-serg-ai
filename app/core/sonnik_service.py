import logging

from openai import APIConnectionError, APIError, APIStatusError, OpenAI, RateLimitError

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


class SonnikService:
    """Сервис для интерпретации снов с использованием AI."""

    def __init__(self):
        """Инициализация сервиса сонника."""
        logger.info('Инициализация сервиса сонника')

    def _generate_prompt(self, dream_text: str, is_premium: bool) -> tuple[str, str]:
        """
        Генерирует системный и пользовательский промпты для модели.
            
        """
        # TODO: Заменить на актуальный промпт от пользователя
        system_prompt_template = f'''
        Ты — доброжелательный интерпретатор снов. Даёшь спокойные, обнадёживающие объяснения без мистических страшилок и без гадания будущего.

        Жёсткие запреты:
        Никаких прогнозов и «у тебя будет/случится».
        Никаких советов/призывов: запрещены «важно», «нужно», «следует», «прислушайся», «сделай», «стоит»
        Запрещены англицизмы, общие слова-пустышки («процесс», «ресурс/ресурсы», «возможности»), туман («подсознание показывает…»).
        Стоп-слова: катастрофа, крушение, ужас, страх, паника, смерть, убийство, болезнь, травма, рана, насилие, неудача, провал, конец, гибель, тревога, кошмар, похороны, убыточный, токсичный.
        Стоп-клише: «очищение/перестройка организма», «высокие вибрации», «в тебе созревает», «освобождение от того, что не служит», «место для нового».
        Избегай формулы «это про …» — вместо неё используй «обозначает», «указывает», «намекает».
        Запрещены модальные/назидающие конструкции: «нужно», «необходимо», «стоит», «следует», «подсказывает/подталкивает», «важно».
        Запрещены расплывчатые абстракции: «ценности», «истинные желания», «идентичность», «перемены» без уточняющего образа. Вместо них — конкретные формулировки, привязанные к образам сна («пустой паспорт — нет отметки/подписанного согласия внутри»).

        Стиль и объём:
        Один абзац, 120–150 слов. Если объём <120 слов — дополни до 120–150. Если >150 — сократи.
        Только на русском, на «ты».
        Слово «энергия» максимум один раз и только в связке с конкретной ситуацией/эмоцией.
        Без конкретных сфер и персонажей: не упоминай «работа», «коллега», «переезд», «отношения», «начальник», «бывший» и т. п. Контекст давай как нейтральные шаблоны («важная тема», «личные договорённости», «условия», «границы»), без прогнозов.

        Логика вывода:
        Назови 1–2 главных образа сна и чётко скажи, что они символизируют (как в метафоре) именно в этом сне..
        «Почему сейчас» формулируй как универсальный шаблон: «это обычно всплывает, когда есть…» (без привязки к сферам).
        Дай причинные связки с «потому что» / «поэтому».
        Позитивный вывод: про прояснение, голос, границы, устойчивость — без советов и аффирмаций.

        Формат ответа:
        Ровно один абзац 120–150 слов.
        Без списков, без обращений к будущему («будет/случится»).
        Не повторяй формулировки, избегай общих штампов.

        Пример-эталон (ориентир стиля и логики):
        Поезд — про ритм решений, а станция, которую ты пропускаешь, про выбор «позже, а не сейчас». Проводник без лица — знак безличных правил и внешних расписаний, которые будто сильнее личных намерений. Июльский снег парадоксально охлаждает ожидания, намекая: планы меняются не по календарю. Это пришло сейчас, потому что рядом тема разговора с важным человеком или пересмотра рабочих договорённостей: ты сверяешь, что твоё, а что навязано. Грусть понятна — она появляется, когда приходится отпускать привычный маршрут, даже если он не вёл туда, куда хотелось. Поэтому сон аккуратно показывает: «ещё рано» — это не запрет, а передышка перед точным поворотом, и когда темп вокруг уляжется, твой собственный ритм снова станет ведущим.

        Ответ
        Верни один абзац 120–150 слов на русском языке, соблюдая все правила выше.
        '''

        user_prompt = f'Проанализируй следующий сон:\n\n{dream_text}\n\nИнтерпретация:'

        return system_prompt_template, user_prompt

    def get_interpretation(self, dream_text: str, premium: bool, model: str) -> str:
        """
        Получает интерпретацию сна от модели ИИ.
        
        Args:
            dream_text: Текст сна для интерпретации
            premium: Флаг премиум-подписки
            model: Название модели для использования
            
        Returns:
            Интерпретация сна
            
        Raises:
            ServiceUnavailableError: Если сервис недоступен
            AIError: При ошибках взаимодействия с AI API
        """
        try:
            self.config = Settings().get_model_config(model_name=model)
            self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])

            system_prompt, user_prompt = self._generate_prompt(dream_text, premium)

            # Обработка специальных моделей Yandex
            processed_model = self.config.get('model_name', model)
            if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
                processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"

            logger.info(f'Отправка запроса к AI API для интерпретации сна. Модель: {model}, Premium: {premium}')
            
            response = self.client.chat.completions.create(
                model=processed_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                temperature=0.45,
                top_p=0.9,
                frequency_penalty=0.7,
                presence_penalty=0.1,
                stream=False,
            )
            
            interpretation = response.choices[0].message.content
            logger.info('Ответ от AI API получен успешно.')
            
            interpretation = self._clean_interpretation(interpretation)
            return interpretation.strip() if interpretation else '(Пустая интерпретация от AI)'

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
        except APIConnectionError as e:
            logger.error(f'Ошибка соединения с AI API: {e}', exc_info=True)
            raise AIConnectionError(f'Не удалось подключиться к AI API: {e}') from e
        except APIError as e:
            logger.error(f'Общая ошибка AI API: {e}', exc_info=True)
            raise AIError(f'Общая ошибка AI API: {e}') from e
        except Exception as e:
            logger.error(f'Неожиданная ошибка при вызове AI API: {e}', exc_info=True)
            raise AIError(f'Внутренняя ошибка при взаимодействии с AI: {e}') from e

    def _clean_interpretation(self, interpretation: str) -> str:
        """
        Очищает интерпретацию от лишних символов и форматирования.
        
        Args:
            interpretation: Сырая интерпретация от AI
            
        Returns:
            Очищенная интерпретация
        """
        # Удаляем лишние пробелы и переносы строк
        interpretation = interpretation.strip()
        # Заменяем множественные пробелы на одинарные
        import re
        interpretation = re.sub(r'\s+', ' ', interpretation)
        return interpretation


# --- Синглтон Экземпляр Сервиса ---
try:
    sonnik_service = SonnikService()
    logger.info('Сервис сонника успешно инициализирован')
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр SonnikService: {e}', exc_info=True)
    sonnik_service = None
