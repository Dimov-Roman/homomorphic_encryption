FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY config.py .
COPY party1.py .
COPY party2.py .

# Создание директории для shared файлов
RUN mkdir -p /shared

# Команда по умолчанию (будет переопределена в docker-compose)
CMD ["python", "party1.py"]
