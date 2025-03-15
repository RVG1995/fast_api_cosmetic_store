#!/bin/bash

# Установка переменных окружения для режима разработки
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_PASSWORD=""
export AUTH_SERVICE_URL=http://localhost:8000
export CART_SERVICE_URL=http://localhost:8002
export ORDER_SERVICE_URL=http://localhost:8003
export PRODUCT_SERVICE_URL=http://localhost:8001
export LOG_LEVEL=DEBUG

# Добавляем текущую директорию в PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
echo "PYTHONPATH установлен: $PYTHONPATH"

# Проверяем доступность Redis вместо запуска нового контейнера
check_redis() {
    if timeout 1 bash -c "</dev/tcp/$REDIS_HOST/$REDIS_PORT" >/dev/null 2>&1; then
        echo "Redis доступен на $REDIS_HOST:$REDIS_PORT"
        return 0
    else
        echo "Предупреждение: Redis недоступен на $REDIS_HOST:$REDIS_PORT"
        echo "Убедитесь, что Redis запущен перед использованием Celery"
        return 1
    fi
}

# Определение действия
ACTION=${1:-all}

# Функция для запуска worker напрямую через модуль python
start_worker() {
    echo "Starting Celery worker..."
    # Выводим информацию о Python и путях
    python -c "import sys; print('Python path:', sys.path)"
    python -c "import celery; print('Celery version:', celery.__version__)"
    # Запускаем через celery
    python -m celery -A celery_app worker -Q celery,auth,cart,order,product --loglevel=$LOG_LEVEL --concurrency=2
}

# Функция для запуска beat напрямую через модуль python
start_beat() {
    echo "Starting Celery beat..."
    python -m celery -A celery_app beat --loglevel=$LOG_LEVEL
}

# Функция для запуска flower напрямую через модуль python
start_flower() {
    echo "Starting Flower monitoring..."
    python -m celery -A celery_app flower --port=5555 --loglevel=$LOG_LEVEL
}

# Проверяем доступность Redis перед запуском
check_redis

# Выполнение команд в зависимости от указанного действия
case "$ACTION" in
    worker)
        start_worker
        ;;
    beat)
        start_beat
        ;;
    flower)
        start_flower
        ;;
    all)
        # Запуск всех компонентов в разных терминалах (для Linux/macOS)
        if [ "$(uname)" == "Darwin" ] || [ "$(uname)" == "Linux" ]; then
            gnome-terminal -- bash -c "$(declare -f start_worker); start_worker" || \
            xterm -e "$(declare -f start_worker); start_worker" || \
            start_worker &
            
            gnome-terminal -- bash -c "$(declare -f start_beat); start_beat" || \
            xterm -e "$(declare -f start_beat); start_beat" || \
            start_beat &
            
            gnome-terminal -- bash -c "$(declare -f start_flower); start_flower" || \
            xterm -e "$(declare -f start_flower); start_flower" || \
            start_flower
        else
            # Для Windows можно использовать команду start в cmd
            # Но здесь просто выводим сообщение
            echo "On Windows, please run each component in a separate terminal:"
            echo "1. python -m celery -A celery_app worker --loglevel=DEBUG --concurrency=2"
            echo "2. python -m celery -A celery_app beat --loglevel=DEBUG"
            echo "3. python -m celery -A celery_app flower --port=5555 --loglevel=DEBUG"
        fi
        ;;
    *)
        echo "Usage: $0 [worker|beat|flower|all]"
        exit 1
        ;;
esac 