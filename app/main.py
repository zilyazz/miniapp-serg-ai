import logging

from fastapi import FastAPI
from app.api.v1.endpoints import divination, sonnik, compatibility, tarot, chiromancy, horoscope

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='Divination Generator API',
    description='Микросервис для интерпретации рунических раскладов.',
    version='0.1.0',
)

app.include_router(divination.router, prefix='/api/v1/divination', tags=['Divination V1'])
app.include_router(sonnik.router, prefix='/api/v1/sonnik', tags=['Sonnik V1'])
app.include_router(compatibility.router, prefix='/api/v1/compatibility', tags=['Compatibility V1'])
app.include_router(tarot.router, prefix='/api/v1/tarot', tags=['Tarot V1'])
app.include_router(chiromancy.router, prefix='/api/v1/chiromancy', tags=['Chiromancy V1'])
app.include_router(horoscope.router, prefix='/api/v1/horoscope', tags=['Horoscope V1'])


@app.get('/', tags=['Root'])
def read_root():
    logger.info('Запрос к корневому эндпоинту /')
    return {'message': 'Welcome to the Divination Generator API! Documentation is available at /docs'}
