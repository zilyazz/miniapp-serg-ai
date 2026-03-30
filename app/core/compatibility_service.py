import json
import logging
import re
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from app.api.v1.schemas import CompatibilityData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompatibilityService:
    """Сервис для анализа совместимости с использованием AI."""

    def __init__(self):
        """Инициализация сервиса совместимости."""
        logger.info('Инициализация сервиса совместимости')

    def _format_aspect_name(self, planet: str) -> str:
        """Преобразует название планеты в читаемый формат."""
        planet_map = {
            'sun': 'Солнце',
            'moon': 'Луна',
            'mercury': 'Меркурий',
            'venus': 'Венера',
            'mars': 'Марс',
            'jupiter': 'Юпитер',
            'saturn': 'Сатурн',
            'asc': 'Асцендент',
        }
        return planet_map.get(planet.lower(), planet)

    def _format_aspect_type(self, aspect_type: str) -> str:
        """Преобразует тип аспекта в читаемый формат."""
        aspect_map = {
            'conjunction': 'соединение',
            'sextile': 'секстиль',
            'square': 'квадрат',
            'trine': 'тригон',
            'opposition': 'оппозиция',
        }
        return aspect_map.get(aspect_type.lower(), aspect_type)

    def _generate_prompt(self, data: 'CompatibilityData') -> tuple[str, str]:
        """
        Генерирует системный и пользовательский промпты для модели.
        
        Args:
            data: Структурированные данные для анализа совместимости
            
        Returns:
            Кортеж (system_prompt, user_prompt)
        """
        system_prompt = '''Ты — астрологический интерпретатор синстрии. Получаешь уже посчитанные показатели и НЕ считаешь астрологию заново.
        Пиши по-русски. 220–300 слов. Тон: доброжелательный, уважительный, без инфантилизма.

        Формат ответа (строго):
        1) Мини-саммари (3 короткие строки, без терминов и аспектов), заголовок: «Суть за 10 секунд:»
          — строка 1: главный ресурс пары простыми словами
          — строка 2: ещё один ресурс
          — строка 3: ключевая тема для бережной настройки
        2) Интерпретация (2–3 абзаца без маркеров). Используй только вход:
          – mode=friendship/romance: подбирай лексику и советы под режим.
          – Если stats.has_asc=true, один раз напиши: «есть контакт с Асцендентом».
          – top_aspects[{a,b,type,weight}] — единственный источник аспектов. Каждый упомяни ровно один раз.
          – Позитивные (weight>0) трактуй как ресурс; отрицательные — как зону настройки (без слов «негатив/напряжение/неудача»).
          – Допускается до 3 формул вида: Планета–Планета — <аспект> → <следствие>. Без скобок и кавычек.
            В «зонах внимания» — максимум 2 такие формулы. Остальные аспекты — короткими фразами.
        3) 1–2 практичных совета, напрямую вытекающих из указанных аспектов и текущего mode.
        4) Позитивный финал одной фразой (без вводных слов).

        Глоссарий для текста:
        sun=Солнце, moon=Луна, mercury=Меркурий, venus=Венера, mars=Марс, jupiter=Юпитер, saturn=Сатурн, asc=Асцендент;
        conjunction=соединение, sextile=секстиль, square=квадрат, trine=тригон, opposition=оппозиция.

        Антитоксичность (строго):
        Запрещены образы «на грани», «трещины», «ломается», «обязанность вместо радости», «фатально/безнадёжно».
        Про минусы говори как о «теме для настройки/договорённости/выравнивания».
        Не раскрывать ход мыслей, не пересчитывать, не сравнивать числа, не давать мед/фин/юр советы, не обещать «судьбу».
        Минимум 60% текста посвяти ресурсам.'''
        
        # Формируем пользовательский промпт с данными в структурированном формате
        aspects_data = [
            {
                'a': asp.a,
                'b': asp.b,
                'type': asp.type,
                'weight': asp.weight
            }
            for asp in data.top_aspects
        ]
        
        input_data = {
            'mode': data.mode,
            'score': data.score,
            'label': data.label,
            'person_a': {
                'name': data.person_a.name,
                'gender': data.person_a.gender,
                'element': data.person_a.element
            },
            'person_b': {
                'name': data.person_b.name,
                'gender': data.person_b.gender,
                'element': data.person_b.element
            },
            'top_aspects': aspects_data,
            'stats': {
                'harmonious_count': data.stats.harmonious_count,
                'challenging_count': data.stats.challenging_count,
                'has_asc': data.stats.has_asc
            }
        }
        
        # Преобразуем данные в JSON для передачи модели
        data_json = json.dumps(input_data, ensure_ascii=False, indent=2)
        
        user_prompt = f'''Проанализируй следующие данные синстрии:

{data_json}

Интерпретация:'''

        return system_prompt, user_prompt

    def get_interpretation(self, data: 'CompatibilityData', premium: bool, model: str) -> str:
        """
        Получает анализ совместимости от модели ИИ.
        
        Args:
            data: Структурированные данные для анализа совместимости
            premium: Флаг премиум-подписки (используется для метрик)
            model: Название модели для использования
            
        Returns:
            Анализ совместимости
            
        Raises:
            ServiceUnavailableError: Если сервис недоступен
            AIError: При ошибках взаимодействия с AI API
        """
        try:
            self.config = Settings().get_model_config(model_name=model)
            self.client = OpenAI(api_key=self.config['api_key'], base_url=self.config['base_url'])

            system_prompt, user_prompt = self._generate_prompt(data)

            # Обработка специальных моделей Yandex
            processed_model = model
            if model in ['yandex-gpt-lite', 'yandexgpt-lite', 'yandex-gpt-3.5-turbo', 'yandexgpt-5-lite']:
                processed_model = f"gpt://{self.config['yandex_cloud_folder']}/yandexgpt/latest"

            logger.info(f'Отправка запроса к AI API для анализа совместимости. Модель: {model}, Premium: {premium}')
            
            response = self.client.chat.completions.create(
                model=processed_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.1,
                stream=False,
            )
            
            interpretation = response.choices[0].message.content
            logger.info('Ответ от AI API получен успешно.')
            
            interpretation = self._clean_interpretation(interpretation)
            return interpretation.strip() if interpretation else '(Пустой анализ совместимости от AI)'

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
        Очищает анализ совместимости от лишних символов, сохраняя структуру.
        
        Args:
            interpretation: Сырой анализ от AI
            
        Returns:
            Очищенный анализ с сохранением форматирования
        """
        # Удаляем только начальные и конечные пробелы
        interpretation = interpretation.strip()
        # Удаляем множественные пустые строки, но сохраняем одиночные переносы
        interpretation = re.sub(r'\n{3,}', '\n\n', interpretation)
        # Удаляем множественные пробелы внутри строк, но сохраняем переносы строк
        lines = interpretation.split('\n')
        cleaned_lines = [re.sub(r' +', ' ', line.strip()) for line in lines]
        interpretation = '\n'.join(cleaned_lines)
        return interpretation


# --- Синглтон Экземпляр Сервиса ---
try:
    compatibility_service = CompatibilityService()
    logger.info('Сервис совместимости успешно инициализирован')
except Exception as e:
    logger.critical(f'Не удалось создать экземпляр CompatibilityService: {e}', exc_info=True)
    compatibility_service = None

