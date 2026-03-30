import logging

from fastapi import APIRouter, HTTPException, status

from app.api.v1.schemas import (
    TarotDayRequest,
    TarotDayResponse,
    TarotRequest,
    TarotResponse,
    TarotFollowupRequest,
    TarotFollowupResponse,
)
from app.core.models import (
    AIClientError,
    AIConnectionError,
    AIError,
    AIServerError,
    InsufficientBalanceError,
    RateLimitExceededError,
    ServiceUnavailableError,
)
from app.core.tarot_service import tarot_service
from app.core.tarot_day_service import tarot_day_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    '/day',
    response_model=TarotDayResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса к AI API (неверные параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
def interpret_tarot_day(request: TarotDayRequest):
    """
    Принимает готовый prompt для интерпретации карты дня и возвращает ответ модели.

    Args:
        request: Запрос с готовым prompt и названием модели

    Returns:
        Интерпретация карты дня
    """
    if tarot_day_service is None:
        logger.critical('Попытка вызова /day при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )

    prompt_trimmed = request.prompt.strip()
    if not prompt_trimmed:
        logger.error('Получен пустой prompt для tarot day')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Поле prompt обязательно для заполнения.',
        )

    logger.info(
        f'Получен запрос на tarot day: '
        f'PromptLength={len(prompt_trimmed)}, Модель={request.model}'
    )

    try:
        interpretation = tarot_day_service.get_interpretation(
            prompt=prompt_trimmed,
            model=request.model,
        )
        logger.info(f'Сгенерирована интерпретация tarot day длиной {len(interpretation)} символов.')
        return TarotDayResponse(interpretation=interpretation)

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
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /day: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Внутренняя ошибка сервера.'
        )


@router.post(
    '/interpret',
    response_model=TarotResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса к AI API (неверные параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
def interpret_tarot(request: TarotRequest):
    """
    Принимает расклад Таро (карты, вопрос, тип расклада) и возвращает интерпретацию.
    
    Args:
        request: Запрос с данными расклада Таро
        
    Returns:
        Интерпретация расклада Таро
    """
    if tarot_service is None:
        logger.critical('Попытка вызова эндпоинта при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )
    
    logger.info(
        f'Получен запрос на интерпретацию Таро: '
        f'Карты={request.tarot}, Вопрос={request.question[:50]}..., '
        f'Тип={request.type}'
    )
    
    try:
        interpretation = tarot_service.get_interpretation(
            tarot=request.tarot,
            question=request.question,
            spread_type=request.type,
            premium=request.premium,
            model=request.model
        )
        logger.info(f'Сгенерирована интерпретация Таро длиной {len(interpretation)} символов.')
        return TarotResponse(interpretation=interpretation)

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
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /interpret: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='Внутренняя ошибка сервера.'
        )


@router.post(
    '/followup',
    response_model=TarotFollowupResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса к AI API (неверные параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
def interpret_tarot_followup(request: TarotFollowupRequest):
    """
    Принимает продолжение расклада Таро с историей предыдущих раскладов и новой картой.
    
    Args:
        request: Запрос с историей раскладов, новой картой и вопросом
        
    Returns:
        Интерпретация продолжения расклада Таро
    """
    if tarot_service is None:
        logger.critical('Попытка вызова эндпоинта при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )
    
    logger.info(
        f'Получен запрос на продолжение расклада Таро: '
        f'Новая карта={request.new_card}, Вопрос={request.question[:50]}..., '
        f'История: {len(request.history)} элементов'
    )
    
    try:
        # Конвертируем Pydantic модели в словари для передачи в сервис
        history_dicts = [
            {
                'question': item.question,
                'cards': item.cards,
                'interpretation': item.interpretation,
                'kind': item.kind,
                'seq': item.seq
            }
            for item in request.history
        ]
        
        interpretation = tarot_service.get_followup_interpretation(
            history=history_dicts,
            new_card=request.new_card,
            question=request.question,
            premium=request.premium,
            model=request.model
        )
        
        logger.info(f'Сгенерирована интерпретация продолжения Таро длиной {len(interpretation)} символов.')
        return TarotFollowupResponse(interpretation=interpretation)

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
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /followup: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='Внутренняя ошибка сервера.'
        )
