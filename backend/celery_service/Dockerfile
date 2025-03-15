FROM python:3.11-slim

WORKDIR /app

# Копируем файл с зависимостями в контейнер
COPY requirements.txt .

# Устанавливаем все необходимые зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код сервиса в контейнер
COPY . .

# Создаем непривилегированного пользователя для запуска приложения
RUN adduser --disabled-password --gecos "" celery_user
USER celery_user

# Две команды для запуска - worker и beat
# Пустые CMD и ENTRYPOINT, так как они будут переопределены в docker-compose.yml
CMD []
ENTRYPOINT [] 