from pydantic import BaseModel, Field
from typing import Any, Dict, Literal


class DivinationRequest(BaseModel):
    runes: list[str]
    theme: str
    type: str
    premium: bool
    model: str


class DivinationResponse(BaseModel):
    interpretation: str


class SonnikRequest(BaseModel):
    """Запрос на интерпретацию сна."""
    dream_text: str
    premium: bool
    model: str


class SonnikResponse(BaseModel):
    """Ответ с интерпретацией сна."""
    interpretation: str


class PersonData(BaseModel):
    """Данные о человеке."""
    name: str
    gender: Literal['male', 'female']
    element: str


class AspectData(BaseModel):
    """Данные об аспекте."""
    a: str
    b: str
    type: Literal['conjunction', 'sextile', 'square', 'trine', 'opposition']
    weight: int


class StatsData(BaseModel):
    """Статистика совместимости."""
    harmonious_count: int
    challenging_count: int
    has_asc: bool


class CompatibilityData(BaseModel):
    """Данные для анализа совместимости."""
    mode: Literal['romance', 'friendship']
    score: int
    label: str
    person_a: PersonData
    person_b: PersonData
    top_aspects: list[AspectData]
    stats: StatsData


class CompatibilityRequest(BaseModel):
    """Запрос на анализ совместимости."""
    data: CompatibilityData
    premium: bool
    model: str


class CompatibilityResponse(BaseModel):
    """Ответ с результатом анализа совместимости."""
    interpretation: str


class TarotRequest(BaseModel):
    """Запрос на интерпретацию расклада Таро."""
    tarot: list[str]  # Выпавшие карты
    question: str  # Вопрос пользователя
    type: str  # Тип расклада
    premium: bool  # Является ли юзер премиум игроком
    model: str  # Модель для использования


class TarotResponse(BaseModel):
    """Ответ с интерпретацией расклада Таро."""
    interpretation: str


class TarotHistoryItem(BaseModel):
    """Элемент истории расклада Таро."""
    question: str  # Вопрос
    cards: list[str]  # Выпавшие карты
    interpretation: str  # Интерпретация
    kind: Literal['main', 'followup']  # Тип расклада: основной или продолжение
    seq: int  # Порядковый номер в истории


class TarotFollowupRequest(BaseModel):
    """Запрос на продолжение расклада Таро."""
    history: list[TarotHistoryItem]  # История предыдущих раскладов
    new_card: str  # Новая выпавшая карта (одна карта для продолжения)
    question: str  # Новый вопрос для продолжения
    premium: bool  # Является ли юзер премиум игроком
    model: str  # Модель для использования


class TarotFollowupResponse(BaseModel):
    """Ответ с интерпретацией продолжения расклада Таро."""
    interpretation: str


class TarotDayRequest(BaseModel):
    """Запрос на интерпретацию карты дня по готовому prompt."""
    prompt: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


class TarotDayResponse(BaseModel):
    """Ответ с интерпретацией карты дня."""
    interpretation: str


class ChiromancyResponse(BaseModel):
    """Ответ с интерпретацией хиромантии по фото руки."""
    interpretation: str


class HoroscopePayload(BaseModel):
    """Payload для запроса гороскопа."""
    day: str  # Дата в формате YYYY-MM-DD
    sign: str  # Русское название знака зодиака
    day_params_ru: str  # Параметры дня на русском языке
    sign_profile_ru: str  # Параметры профиля знака на русском языке (может быть пустой строкой)
    allowed_tags_en: list[str]  # Массив допустимых EN-тегов


class HoroscopeRequest(BaseModel):
    """Запрос на генерацию гороскопа по знаку и дню."""
    payload: HoroscopePayload
    model: str  # Модель для использования


class HoroscopeContent(BaseModel):
    """Содержимое гороскопа на русском языке."""
    general_public: str  # Public (1 абзац; не короче 110 символов)
    general_premium: str  # Premium (продолжение public; минимум 2 абзаца; не короче 180 символов)


class HoroscopeResponse(BaseModel):
    """Ответ с гороскопом по знаку и дню."""
    content_ru: HoroscopeContent
    tags: list[str]  # Массив тегов (может быть пустым)
    scores: Dict[str, float]  # Объект с оценками (может быть пустым)


class LuckyDayPayload(BaseModel):
    """Payload для запроса анализа удачного дня."""
    query_ru: str  # Запрос пользователя на русском языке
    allowed_tags_en: list[str]  # Массив допустимых EN-тегов
    allowed_score_keys: list[str]  # Массив допустимых ключей для scores


class LuckyDayRequest(BaseModel):
    """Запрос на анализ удачного дня."""
    payload: LuckyDayPayload
    model: str | None = None  # Модель для использования (опционально, по умолчанию используется QWEN3_NEXT_80B)


class LuckyDayResponse(BaseModel):
    """Ответ с анализом удачного дня."""
    intent_tags: list[str]  # Теги дня, которые подходят под цель
    avoid_tags: list[str]  # Теги, которые нежелательны
    weights_scores: Dict[str, float]  # Веса параметров дня в диапазоне [-1..1]
    best_text_ru: str  # Описание, почему такой день подходит под запрос
