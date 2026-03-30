FROM python:3.12-slim

WORKDIR /app

# Копируем файлы для установки
COPY pyproject.toml README.md ./

# Копируем код приложения сразу (важно!)
COPY app app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install

EXPOSE 8080

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]