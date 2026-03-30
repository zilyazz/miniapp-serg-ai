import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.v1.schemas import ChiromancyResponse
from app.core.models import (
    AIClientError,
    AIConnectionError,
    AIError,
    AIServerError,
    InsufficientBalanceError,
    RateLimitExceededError,
    ServiceUnavailableError,
)
from app.core.chiromancy_service import chiromancy_service
from app.core.const import QWEN3_VL_32B

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    '/interpret',
    response_model=ChiromancyResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {'description': 'Сервис временно недоступен'},
        status.HTTP_502_BAD_GATEWAY: {'description': 'Ошибка на стороне AI API (проблема с подключением)'},
        status.HTTP_402_PAYMENT_REQUIRED: {'description': 'Недостаточно средств на балансе AI API'},
        status.HTTP_429_TOO_MANY_REQUESTS: {'description': 'Превышен лимит запросов к AI API'},
        status.HTTP_400_BAD_REQUEST: {'description': 'Ошибка запроса (неверный формат файла или параметры)'},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {'description': 'Внутренняя ошибка сервера'},
    },
)
async def interpret_chiromancy(
    image: UploadFile = File(...),
    hand: str = Form(..., description="Рука пользователя: 'right' (правая) или 'left' (левая)")
):
    """
    Принимает фото руки и возвращает интерпретацию по хиромантии.
    
    Args:
        image: Файл изображения руки (image/jpeg, image/png, image/webp)
        hand: Рука пользователя - 'right' (правая) или 'left' (левая)
        
    Returns:
        Интерпретация хиромантии по фото руки
    """
    if chiromancy_service is None:
        logger.critical('Попытка вызова эндпоинта при неинициализированном сервисе.')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Сервис временно недоступен из-за ошибки инициализации.',
        )
    
    # Валидация параметра hand
    if hand not in ('right', 'left'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр 'hand' должен быть 'right' (правая) или 'left' (левая)"
        )
    
    logger.info(
        f'Получен запрос на интерпретацию хиромантии: '
        f'Файл={image.filename}, Тип={image.content_type}, Размер={image.size if hasattr(image, "size") else "неизвестен"}, Рука={hand}'
    )
    
    try:
        # Чтение содержимого файла
        image_content = await image.read()
        content_type = image.content_type or 'application/octet-stream'
        
        # Вызов сервиса для получения интерпретации
        # Используем Qwen3-VL-32B-Instruct - vision модель специально для хиромантии
        interpretation = chiromancy_service.get_interpretation(
            image_content=image_content,
            content_type=content_type,
            hand=hand,
            model=QWEN3_VL_32B
        )
        
        logger.info(f'Сгенерирована интерпретация хиромантии длиной {len(interpretation)} символов.')
        return ChiromancyResponse(interpretation=interpretation)

    except ValueError as e:
        logger.error(f'Ошибка валидации файла: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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
        logger.error(f'Неожиданная внутренняя ошибка в эндпоинте /interpret: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='Внутренняя ошибка сервера.'
        )
