import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.api.v1.schemas import HoroscopeRequest, HoroscopeResponse, LuckyDayRequest, LuckyDayResponse
from app.core.models import (
    AIError,
    AIClientError,
    AIConnectionError,
    AIServerError,
    InsufficientBalanceError,
    RateLimitExceededError,
    ServiceUnavailableError,
)
from app.core.horoscope_service import horoscope_service
from app.core.lucky_day_service import lucky_day_service
from app.core.const import QWEN3_NEXT_80B

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_date(date_str: str) -> bool:
    """
    Валидирует формат даты YYYY-MM-DD.
    
    Args:
        date_str: Строка с датой
        
    Returns:
        True если дата валидна, False иначе
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


@router.post(
    '/generate',
    response_model=HoroscopeResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса (неверные параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
def generate_horoscope(request: HoroscopeRequest):
    """
    Генерирует гороскоп по знаку зодиака и дате.
    Гороскоп одинаковый для всех пользователей одного знака на одну дату.
    
    Args:
        request: Запрос с данными для генерации гороскопа
        
    Returns:
        Гороскоп в структурированном формате
    """
    if horoscope_service is None:
        logger.critical('Попытка вызова эндпоинта при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )
    
    # Валидация входных данных
    if not _validate_date(request.payload.day):
        logger.error(f'Неверный формат даты: {request.payload.day}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Неверный формат даты. Ожидается формат YYYY-MM-DD.'
        )
    
    if not request.payload.sign or not request.payload.sign.strip():
        logger.error('Знак зодиака не указан или пустой')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Знак зодиака обязателен для заполнения.'
        )
    
    if not request.payload.day_params_ru or not request.payload.day_params_ru.strip():
        logger.error('Параметры дня не указаны или пустые')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Параметры дня обязательны для заполнения.'
        )
    
    logger.info(
        f'Получен запрос на генерацию гороскопа: '
        f'Знак={request.payload.sign}, Дата={request.payload.day}, Модель={request.model}'
    )
    
    try:
        # Вызов сервиса для генерации гороскопа
        horoscope_data = horoscope_service.get_horoscope(
            day=request.payload.day,
            sign=request.payload.sign,
            day_params_ru=request.payload.day_params_ru,
            sign_profile_ru=request.payload.sign_profile_ru or '',
            allowed_tags_en=request.payload.allowed_tags_en,
            model=request.model
        )
        
        logger.info(
            f'Гороскоп успешно сгенерирован для знака {request.payload.sign} '
            f'на дату {request.payload.day}'
        )
        
        # Формируем ответ в соответствии со схемой
        return HoroscopeResponse(
            content_ru=horoscope_data['content_ru'],
            tags=horoscope_data.get('tags', []),
            scores=horoscope_data.get('scores', {})
        )

    except ServiceUnavailableError as e:
        logger.error(f'Сервис недоступен: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    except InsufficientBalanceError as e:
        logger.error(f'Недостаточно средств: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))

    except RateLimitExceededError as e:
        logger.error(f'Превышен лимит запросов: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    except AIClientError as e:
        logger.error(f'Ошибка клиента AI API ({e.status_code}): {e}', exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=str(e))

    except AIServerError as e:
        logger.error(f'Ошибка сервера AI API ({e.status_code}): {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f'Ошибка на стороне AI сервиса: {e}'
        )

    except AIConnectionError as e:
        logger.error(f'Ошибка соединения с AI API: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f'Ошибка подключения к AI сервису: {e}'
        )

    except AIError as e:
        logger.error(f'Общая ошибка AI: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f'Внутренняя ошибка при взаимодействии с AI: {e}'
        )

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /generate: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='Внутренняя ошибка сервера.'
        )


@router.post(
    '/lucky',
    response_model=LuckyDayResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса (неверные параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
def analyze_lucky_day(request: LuckyDayRequest):
    """
    Анализирует запрос пользователя и определяет параметры удачного дня.
    Нейросервис анализирует запрос и возвращает подходящие теги, нежелательные теги,
    веса параметров дня и описание.
    
    Args:
        request: Запрос с данными для анализа удачного дня
        
    Returns:
        Результат анализа удачного дня в структурированном формате
    """
    if lucky_day_service is None:
        logger.critical('Попытка вызова эндпоинта при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )
    
    # Валидация входных данных
    query_ru_trimmed = request.payload.query_ru.strip() if request.payload.query_ru else ''
    if not query_ru_trimmed:
        logger.error('Запрос пользователя не указан или пустой')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Поле query_ru обязательно для заполнения.'
        )
    
    if len(query_ru_trimmed) < 5:
        logger.error(f'Запрос пользователя слишком короткий: {len(query_ru_trimmed)} символов')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Поле query_ru должно содержать минимум 5 символов.'
        )
    
    if not request.payload.allowed_tags_en or len(request.payload.allowed_tags_en) == 0:
        logger.error('Массив allowed_tags_en пустой')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Массив allowed_tags_en не может быть пустым.'
        )
    
    if not request.payload.allowed_score_keys or len(request.payload.allowed_score_keys) == 0:
        logger.error('Массив allowed_score_keys пустой')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Массив allowed_score_keys не может быть пустым.'
        )
    
    # Используем модель из запроса, если указана, иначе используем QWEN3_NEXT_80B по умолчанию
    model = request.model if request.model else QWEN3_NEXT_80B
    
    logger.info(
        f'Получен запрос на анализ удачного дня: '
        f'Запрос={query_ru_trimmed[:50]}..., Модель={model}'
    )
    
    try:
        # Вызов сервиса для анализа удачного дня
        lucky_day_data = lucky_day_service.analyze_lucky_day(
            query_ru=query_ru_trimmed,
            allowed_tags_en=request.payload.allowed_tags_en,
            allowed_score_keys=request.payload.allowed_score_keys,
            model=model
        )
        
        logger.info('Анализ удачного дня успешно выполнен')
        
        # Формируем ответ в соответствии со схемой
        return LuckyDayResponse(
            intent_tags=lucky_day_data.get('intent_tags', []),
            avoid_tags=lucky_day_data.get('avoid_tags', []),
            weights_scores=lucky_day_data.get('weights_scores', {}),
            best_text_ru=lucky_day_data.get('best_text_ru', '')
        )

    except ServiceUnavailableError as e:
        logger.error(f'Сервис недоступен: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    except InsufficientBalanceError as e:
        logger.error(f'Недостаточно средств: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))

    except RateLimitExceededError as e:
        logger.error(f'Превышен лимит запросов: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    except AIClientError as e:
        logger.error(f'Ошибка клиента AI API ({e.status_code}): {e}', exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=str(e))

    except AIServerError as e:
        logger.error(f'Ошибка сервера AI API ({e.status_code}): {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f'Ошибка на стороне AI сервиса: {e}'
        )

    except AIConnectionError as e:
        logger.error(f'Ошибка соединения с AI API: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f'Ошибка подключения к AI сервису: {e}'
        )

    except AIError as e:
        logger.error(f'Общая ошибка AI: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f'Внутренняя ошибка при взаимодействии с AI: {e}'
        )

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /lucky: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='Внутренняя ошибка сервера.'
        )
