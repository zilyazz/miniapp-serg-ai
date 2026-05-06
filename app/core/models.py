import json
import logging
import re

from openai import APIConnectionError, APIError, APIStatusError, OpenAI, RateLimitError

from app.core.config import Settings
from app.core.const import EXAMPLE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Кастомные Исключения ---


class DivinationError(Exception):
    """Базовый класс для ошибок сервиса гаданий."""
    pass


class ExamplesLoadError(DivinationError):
    """Ошибка при загрузке файла примеров."""
    pass


class ServiceUnavailableError(DivinationError):
    """Сервис недоступен (например, из-за ошибки загрузки примеров)."""
    pass


class AIError(DivinationError):
    """Общая ошибка взаимодействия с AI API."""
    pass


class AIClientError(AIError):
    """Ошибка на стороне клиента при вызове AI API (4xx)."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f'AI API Client Error {status_code}: {message}')


class InsufficientBalanceError(AIClientError):
    """Недостаточно средств на балансе AI API (402)."""
    def __init__(self, message: str):
        super().__init__(402, message)


class RateLimitExceededError(AIClientError):
    """Превышен лимит запросов к AI API (429)."""
    def __init__(self, message: str):
        super().__init__(429, message)


class AIServerError(AIError):
    """Ошибка на стороне сервера AI API (5xx)."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f'AI API Server Error {status_code}: {message}')


class AIConnectionError(AIError):
    """Ошибка соединения с AI API."""
    pass

class DivinationService:
    def __init__(self):
        self.examples_path = EXAMPLE_PATH
        self._examples: list[tuple[list[str], str]] | None = None
        self._load_error: Exception | None = None
        try:
            self._examples = self._load_examples()
            if not self._examples:
                logger.warning('Список примеров пуст после загрузки. Генерация может быть неточной.')
            logger.info(f'Примеры успешно загружены из {self.examples_path}')
        except ExamplesLoadError as e:  
            logger.error(f'Критическая ошибка при инициализации сервиса: {e}')
            self._load_error = e

    def _load_examples(self) -> list[tuple[list[str], str]]:
        """Загружает примеры интерпретаций рун из JSON-файла."""
        try:
            with open(self.examples_path, encoding='utf-8') as file:
                data = json.load(file)
                if not isinstance(data, dict):
                    raise ValueError('Ожидался словарь в JSON.')
                examples = []
                for key, value in data.items():
                    if isinstance(value, dict) and 'runes' in value and 'description' in value:
                        if isinstance(value['runes'], list) and isinstance(value['description'], str):
                            examples.append((value['runes'], value['description']))
                        else:
                            logger.warning(f'Некорректный тип данных для ключа {key} в {self.examples_path}')
                    else:
                        logger.warning(f'Отсутствуют необходимые ключи {key} в {self.examples_path}')
                return examples
        except FileNotFoundError:
            raise ExamplesLoadError(f'Файл с примерами не найден: {self.examples_path}')
        except json.JSONDecodeError as e:
            raise ExamplesLoadError(f'Ошибка декодирования JSON в файле {self.examples_path}: {e}')
        except ValueError as e:
            raise ExamplesLoadError(f'Ошибка формата данных в файле {self.examples_path}: {e}')
        except Exception as e:
            raise ExamplesLoadError(f'Неожиданная ошибка при загрузке примеров из {self.examples_path}: {e}')

    def _generate_prompt(self, runelist: list[str], theme: str, type: str, is_premium: bool) -> tuple[str, str]:
        """Генерирует системный и пользовательский промпты для модели."""
        if is_premium:
            length_promt = '''Генерируй ровно 130 - 170 слов. Обязательно заверши расклад рекомендацией (опираясь на итог расклада) в одно предложение, начиная с фразы «Совет:».'''
        else:
            length_promt = '''Ответ должен быть кратким и гладким, 85-95 слов, с ясным описанием ключевых аспектов расклада и позитивным тоном'''
        
        if type == "pyramid":
            positions_description = """
            Позиция 1 — это ваше возможное нынешнее мироощущение, то, что влияет на вас сейчас. 
            Позиция 2 — источник вашей сил и поддержки, откуда вы черпаете энергию.
            Позиция 3 — то, что ослабляет или негативно влияет на вас..
            Позиция 4 — возможность получить ценный опыт, обучение или совет.
            Позиция 5 — от чего стоит отказаться, какие негативные моменты в своей жизни следует минимизировать. Необходимость выбора.
            Позиция 6 — перспективы ближайшего будущего.
            Позиция 7 — неожиданные события, как приятные, так и неприятные.
            """
        elif type == "cross":
            positions_description = """
            Позиция 1 — истоки ситуации, её корни в прошлом.
            Позиция 2 — ваше текущее состояние и внутренние ресурсы.
            Позиция 3 — возможные направления развития событий.
            Позиция 4 — скрытые мотивы или влияния.
            Позиция 5 — вызовы, с которыми предстоит столкнуться, и способы их преодоления.
            Позиция 6 — вероятный итог или результат ситуации.
            """
        elif type == "classic":
            positions_description = """
            Первая руна — причина ситуации, идущая из прошлого.
            Вторая руна — ваше настоящее и рекомендация для действий.
            Третья руна — вероятный исход и уроки, которые вы извлечёте.
            """
        else:
            positions_description = "Описание позиций расклада зависит от его типа."
        
        system_prompt_template = (
        f'''
        Ты – экстрасенс-рунолог, глубоко понимающий символику Старшего Футарка, их перевернутые значения и взаимодействие рун. Интерпретируй расклад, строго учитывая порядок рун, тему вопроса и энергетику перевернутых рун (если они есть).
        
        {length_promt}

        Краткие значения рун с уточнениями:

        Феху – достаток, материальная стабильность (в перевёрнутом положении: потери, неуверенность).
        Уруз – сила, прорыв (перевёрнутая: временное снижение энергии, усталость, необходимость восстановления).
        Турисаз – защита через трансформацию, испытания (перевёрнутая: слабость, нерешительность).
        Ансуз – мудрость, коммуникация (перевёрнутая: обман, ложные советы).
        Райдо – путь, движение (перевёрнутая: препятствия, отсутствие движения).
        Кеназ – ясность, страсть, творчество (перевёрнутая: временные недопонимания, сомнения).
        Гебо – партнерство, равновесие (без перевёрнутого значения).
        Вуньо – радость, успех (перевёрнутая: временные трудности, недопонимания).
        Хагалаз – очищение, перемены, непредсказуемое событие (без перевёрнутого).
        Наутиз – нужда, урок терпения (перевёрнутая: внутренние ограничения).
        Иса – заморозка, пауза (без перевёрнутого).
        Йеро – цикл, заслуженный результат (без перевёрнутого).
        Эйваз - перерождение, трансформация, перезагрузка, обретение внутренней силы и опоры (без перевёрнутого).
        Пертро – тайна, судьба (перевёрнутая: разочарование, обман).
        Альгиз – защита, интуиция (перевёрнутая: предостережение).
        Соул – свет, победа (без перевёрнутого).
        Тейваз – мужество, борьба (перевёрнутая: растрата энергии).
        Беркана – рост, семья (перевёрнутая: препятствия в отношениях).
        Эваз – движение, прогресс (перевёрнутая: вынужденная пауза).
        Манназ – самопознание, социум (перевёрнутая: предательство).
        Лагуз – поток, интуиция (перевёрнутая: самообман).
        Ингуз – завершение, плодородие (без перевёрнутого).
        Дагаз – прорыв, гармония (без перевёрнутого).
        Отал – наследие, дом (перевёрнутая: конфликты в семье).
        Пустая руна Одина – неизвестность, скрытые процессы.

        Тебе дан список рун в том порядке, в каком они легли на позиции. 
        Каждая руна интерпретируется исключительно в рамках своей позиции:
        {positions_description}
        - Запрещено переносить значение руны на позицию с другим номером.
        - Каждая позиция трактуется ТОЛЬКО в контексте её значения, а не по общему смыслу руны. Например, если третья позиция = «что ослабляет», даже позитивная руна описывается как то, что вредит или мешает, но в мягком и обнадёживающем ключе.
        - Запрещено писать вводные общие фразы вроде «В этом раскладе мы видим…», «В раскладе выпало…» или «Руны показывают…». Начинай сразу с описания первой позиции.
        - Не упоминай номера позиций и названия рун в скобках. Включай смысл позиции прямо в текст. Например, если это «то, что вредит», пиши, что эта энергия проявляется как препятствие, сдерживающий фактор, источник трудностей. 
        - Если руна перевёрнута, учитывай только её перевёрнутое значение.
        - Пиши плавно и литературно, избегай повторов слов и близких по смыслу фраз в одном абзаце.
        - Используй слова-маркеры неопределённости: «возможно», «скорее всего», «иногда», «порой».
        - Тон расклада: Тон всегда должен быть ободряющим, с акцентом на перспективы, рост и внутреннюю силу человека. Даже в описании сложных моментов добавляй обнадёживающий оттенок и указывай перспективу улучшения.
        - Даже негативные руны подавай как этап пути, ведущий к лучшему.
        - Финал расклада должен быть вдохновляющим, кратко подводя итог и показывая внутренние ресурсы человека.


        **Важно:**
        - Двигайся от первой позиции к последней, создавая связный рассказ.
        - Не включай в ответ системные сообщения, пояснения или ключ расклада.
        - Не пиши «Связь рун» или похожие разделы.
        - Пиши так, чтобы интерпретация звучала как мягкое предположение, а не абсолютная истина. 
        - Ответ должен быть только интерпретацией расклада, без лишних технических деталей.
        - Генерируй текст только русскими буквами, без латиницы, цифр и специальных символов. 
        - Запрещено вставлять непечатные или иностранные символы.
        - Не используй слова «смерть», «крах», «катастрофа» и другие, вызывающие тревогу.
        '''
        )
        formatted_examples = ''
        # Используем загруженные примеры, если они есть
        examples_to_use = self._examples if self._examples is not None else []
        if not examples_to_use and self._load_error is None:
            logger.warning('Генерация промпта без примеров (список пуст).')
        elif self._load_error is not None:
            logger.warning('Генерация промпта без примеров из-за ошибки их загрузки.')

        for runes, description in examples_to_use:
            formatted_examples += f'Ключ расклада: {runes}\nИнтерпретация: {description}\n\n'

        system_prompt = system_prompt_template + formatted_examples
        user_prompt = f'Проанализируй следующий расклад:\nКлюч расклада: {runelist}\nТема: {theme}\nТип: {type}\nИнтерпретация:'

        return system_prompt, user_prompt

    def get_interpretation(self, runes: list[str], theme: str, type: str, premium: bool, model: str) -> str:
        """Получает интерпретацию расклада от модели ИИ."""
        if self._load_error:
            logger.error('Попытка получить интерпретацию при ошибке загрузки примеров.')
            raise ServiceUnavailableError(f'Сервис недоступен из-за ошибки конфигурации: {self._load_error}')
        
        self.config = Settings().get_model_config(model_name=model)
        self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])
        
        processed_runes = self._preprocess_runes(runes)

        system_prompt, user_prompt = self._generate_prompt(processed_runes, theme, type, premium)

        processed_model = self.config.get('model_name', model)
        if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
            processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"
        try:
            print(system_prompt, user_prompt)
            logger.info(f'Отправка запроса к AI API: Руны={processed_runes}, Тема={theme}, Тип={type}')
            response = self.client.chat.completions.create(
                model=processed_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                stream=False,
                # temperature=0.7,
                # max_tokens=500,
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
        Удаляет ключ расклада, названия рун в скобках и другие технические детали из интерпретации.
        """
        # Удаляем строку с ключом расклада, если она есть
        interpretation = re.sub(r'Ключ расклада:\s*\[.*?\]', '', interpretation, flags=re.IGNORECASE)
        # Удаляем названия рун в скобках (например, "(Феху)", "(Уруз)")
        interpretation = re.sub(r'\([^)]*\)', '', interpretation)
        # Удаляем лишние пробелы и переносы строк
        interpretation = re.sub(r'\s+', ' ', interpretation).strip()
        return interpretation
    
    def _preprocess_runes(self, runes: list[str]) -> list[str]:
        processed_runes = []
        for rune in runes:
            if rune.endswith('*'):
                processed_runes.append(f"{rune[:-1]} (перевёрнутые)")
            else:
                processed_runes.append(rune)
        return processed_runes

# --- Синглтон Экземпляр Сервиса ---
try:
    divination_service = DivinationService()
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр DivinationService: {e}', exc_info=True)
    # Приложение не сможет работать без сервиса. установим divination_service = None,
    # чтобы эндпоинт мог вернуть 503 и будем проверять в эндпоинте.
    divination_service = None
