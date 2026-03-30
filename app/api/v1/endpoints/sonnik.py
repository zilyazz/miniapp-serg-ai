import logging

from fastapi import APIRouter, HTTPException, status

from app.api.v1.schemas import SonnikRequest, SonnikResponse
from app.core.sonnik_service import (
    AIClientError,
    AIConnectionError,
    AIError,
    AIServerError,
    InsufficientBalanceError,
    RateLimitExceededError,
    ServiceUnavailableError,
    sonnik_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    '/interpret',
    response_model=SonnikResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса к AI API (неверные параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
def interpret_dream(request: SonnikRequest):
    """
    Принимает текст сна и возвращает его интерпретацию.
    
    Args:
        request: Запрос с текстом сна, флагом premium и моделью
        
    Returns:
        Интерпретация сна
    """
    if sonnik_service is None:
        logger.critical('Попытка вызова эндпоинта при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )
    
    logger.info(f'Получен запрос на интерпретацию сна. Premium: {request.premium}, Модель: {request.model}')
    
    try:
        interpretation = sonnik_service.get_interpretation(
            dream_text=request.dream_text,
            premium=request.premium,
            model=request.model
        )
        
        logger.info(f'Сгенерирована интерпретация сна длиной {len(interpretation)} символов.')
        return SonnikResponse(interpretation=interpretation)

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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Ошибка на стороне AI сервиса: {e}')

    except AIConnectionError as e:
        logger.error(f'Ошибка соединения с AI API: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Ошибка подключения к AI сервису: {e}')

    except AIError as e:
        logger.error(f'Общая ошибка AI: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Внутренняя ошибка при взаимодействии с AI: {e}'
        )

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /interpret: {e}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Внутренняя ошибка сервера.')
