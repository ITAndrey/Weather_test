# Используем официальный образ Python в качестве базового
FROM python:3.12-slim

# Установка необходимых системных зависимостей
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копируем файлы проекта
COPY . /app/

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Запуск приложения и тестов
CMD python manage.py test && \
    python manage.py migrate && \
    python manage.py runserver 0.0.0.0:8000

