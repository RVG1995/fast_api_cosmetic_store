#!/bin/bash
sleep(){ :; }  # no-op for sleep to speed up startup

# Скрипт для быстрого запуска всех сервисов и фронтенда косметического магазина
# Автор: Claude AI

# Установка цветов для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Директория проекта (текущая директория)
PROJECT_DIR=$(pwd)
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend/app"
LOGS_DIR="$PROJECT_DIR/logs"

# Создаем директорию для логов, если она не существует
mkdir -p "$LOGS_DIR"

# Функция для вывода сообщений
print_message() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

# Функция для проверки наличия директории
check_directory() {
    if [ ! -d "$1" ]; then
        echo -e "${RED}[ERROR]${NC} Директория $1 не существует!"
        return 1
    fi
    return 0
}

# Функция для запуска сервисов
start_service() {
    service_name=$1
    service_dir=$2
    service_cmd=$3
    log_file="$LOGS_DIR/${service_name}.log"
    
    print_message "${GREEN}Запуск сервиса:${NC} $service_name"
    
    # Переходим в директорию сервиса
    cd "$service_dir" || { 
        echo -e "${RED}[ERROR]${NC} Не удалось перейти в директорию $service_dir"; 
        return 1; 
    }
    
    # Запускаем сервис в фоновом режиме и перенаправляем вывод в лог-файл
    eval "$service_cmd" > "$log_file" 2>&1 &
    
    # Получаем PID запущенного процесса
    local pid=$!
    
    # Записываем PID в файл для дальнейшего использования
    echo $pid > "$LOGS_DIR/${service_name}.pid"
    
    # Проверяем, что процесс запустился
    if ps -p $pid > /dev/null; then
        echo -e "${GREEN}[OK]${NC} Сервис $service_name запущен (PID: $pid). Лог: $log_file"
    else
        echo -e "${RED}[ERROR]${NC} Не удалось запустить сервис $service_name"
        return 1
    fi
    
    # Возвращаемся в директорию проекта
    cd "$PROJECT_DIR" || return 1
    return 0
}

# Функция для остановки сервисов
stop_services() {
    print_message "${YELLOW}Остановка всех сервисов...${NC}"
    
    # Останавливаем все процессы
    for pid_file in "$LOGS_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            service_name=$(basename "$pid_file" .pid)
            pid=$(cat "$pid_file")
            
            print_message "Остановка сервиса $service_name (PID: $pid)..."
            kill -15 "$pid" 2>/dev/null
            
            # Проверяем, остановился ли процесс
            sleep 2
            if ps -p "$pid" > /dev/null; then
                echo -e "${RED}[WARNING]${NC} Сервис $service_name не остановился. Принудительная остановка..."
                kill -9 "$pid" 2>/dev/null
            else
                echo -e "${GREEN}[OK]${NC} Сервис $service_name остановлен"
            fi
            
            # Удаляем PID-файл
            rm -f "$pid_file"
        fi
    done
    
    print_message "${GREEN}Все сервисы остановлены${NC}"
    exit 0
}

# Функция для проверки Redis без запуска нового контейнера
start_redis() {
    print_message "Проверка доступности Redis..."
    
    # Проверяем, доступен ли Redis с помощью timeout и curl
    if timeout 1 bash -c "</dev/tcp/localhost/6379" >/dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} Redis доступен на localhost:6379"
        return 0
    else
        echo -e "${YELLOW}[WARNING]${NC} Redis недоступен на localhost:6379"
        echo -e "${YELLOW}[INFO]${NC} Убедитесь, что Redis запущен перед использованием Celery"
        return 1
    fi
}

# Обработка сигналов для корректного закрытия
trap stop_services INT TERM

# Информация о запуске
print_message "${BLUE}====================================${NC}"
print_message "${BLUE}   ЗАПУСК СЕРВИСОВ КОСМЕТИК-СТОР   ${NC}"
print_message "${BLUE}====================================${NC}"
print_message "Директория проекта: ${YELLOW}$PROJECT_DIR${NC}"

# Информация по прерыванию скрипта
print_message "${YELLOW}Для остановки всех сервисов нажмите Ctrl+C${NC}"
echo ""

# Проверяем наличие виртуального окружения для Python
PYTHON_ENV=""

if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    PYTHON_ENV="$PROJECT_DIR/venv/bin/activate"
    print_message "Найдено виртуальное окружение Python в корне проекта"
elif [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
    PYTHON_ENV="$BACKEND_DIR/venv/bin/activate"
    print_message "Найдено виртуальное окружение Python в директории backend"
elif command -v python3 >/dev/null 2>&1; then
    print_message "Виртуальное окружение не найдено, используем системный Python"
else
    print_message "${RED}[ERROR]${NC} Python3 не установлен. Установите Python для запуска бэкенд-сервисов."
    exit 1
fi

# Если найдено виртуальное окружение, активируем его
if [ -n "$PYTHON_ENV" ]; then
    print_message "Активация виртуального окружения Python: $PYTHON_ENV"
    source "$PYTHON_ENV"
fi

# Запуск Redis для Celery
print_message "${BLUE}=== ЗАПУСК REDIS ДЛЯ CELERY ===${NC}"
start_redis

# Запуск Celery и Flower
print_message "${BLUE}=== ЗАПУСК CELERY СЕРВИСОВ ===${NC}"

# Проверяем наличие директории celery_service
if [ -d "$BACKEND_DIR/celery_service" ]; then
    print_message "Директория Celery найдена: $BACKEND_DIR/celery_service"
    
    # Проверяем наличие скрипта run_dev.sh и прав на исполнение
    if [ -f "$BACKEND_DIR/celery_service/run_dev.sh" ]; then
        if [ ! -x "$BACKEND_DIR/celery_service/run_dev.sh" ]; then
            print_message "Устанавливаем права на исполнение для run_dev.sh"
            chmod +x "$BACKEND_DIR/celery_service/run_dev.sh"
        fi
        
        # Запуск Celery worker
        start_service "celery_worker" "$BACKEND_DIR/celery_service" "./run_dev.sh worker"
        sleep 3  # Ждем, чтобы worker успел запуститься
        
        # Запуск Celery beat для планировщика задач
        start_service "celery_beat" "$BACKEND_DIR/celery_service" "./run_dev.sh beat"
        
        # Запуск Flower для мониторинга
        start_service "celery_flower" "$BACKEND_DIR/celery_service" "./run_dev.sh flower"
        sleep 2
        
        print_message "${GREEN}[INFO]${NC} Celery worker, beat и Flower запущены. Мониторинг доступен по адресу: http://localhost:5555"
    else
        print_message "${YELLOW}[WARNING]${NC} Скрипт run_dev.sh не найден. Celery не будет запущен."
    fi
else
    print_message "${YELLOW}[WARNING]${NC} Директория celery_service не найдена. Celery не будет запущен."
fi

echo ""

# Запуск RabbitMQ consumer для email
print_message "${BLUE}=== ЗАПУСК RABBITMQ EMAIL CONSUMER ===${NC}"

if [ -d "$BACKEND_DIR/rabbit/email_consumer" ]; then
    print_message "Директория RabbitMQ Email Consumer найдена: $BACKEND_DIR/rabbit/email_consumer"
    
    # Запуск Email Consumer
    start_service "email_consumer" "$BACKEND_DIR/rabbit/email_consumer" "python consumer.py"
    sleep 2
    
    print_message "${GREEN}[INFO]${NC} RabbitMQ Email Consumer запущен. Обработка сообщений из очередей началась."
else
    print_message "${YELLOW}[WARNING]${NC} Директория email_consumer не найдена. Email Consumer не будет запущен."
fi

echo ""

# Запуск бэкенд-сервисов
print_message "${BLUE}=== ЗАПУСК БЭКЕНД-СЕРВИСОВ ===${NC}"

# Проверяем наличие директории backend
if check_directory "$BACKEND_DIR"; then
    print_message "Директория бэкенда найдена: $BACKEND_DIR"
    
    # Запуск сервиса аутентификации
    if [ -d "$BACKEND_DIR/auth_service" ]; then
        start_service "auth_service" "$BACKEND_DIR/auth_service" "python main.py"
        sleep 2  # Ждем немного, чтобы сервисы запускались последовательно
    fi
    
    # Запуск сервиса товаров
    if [ -d "$BACKEND_DIR/product_service" ]; then
        start_service "product_service" "$BACKEND_DIR/product_service" "python main.py"
        sleep 2
    fi
    
    # Запуск сервиса корзины
    if [ -d "$BACKEND_DIR/cart_service" ]; then
        start_service "cart_service" "$BACKEND_DIR/cart_service" "python main.py"
        sleep 2
    fi
    
    # Запуск сервиса заказов
    if [ -d "$BACKEND_DIR/order_service" ]; then
        start_service "order_service" "$BACKEND_DIR/order_service" "python main.py"
        sleep 2
    fi
    
    # Запуск сервиса отзывов
    if [ -d "$BACKEND_DIR/review_service" ]; then
        start_service "review_service" "$BACKEND_DIR/review_service" "python main.py"
        sleep 2
    fi
    
    # Запуск сервиса уведомлений
    if [ -d "$BACKEND_DIR/notifications_service" ]; then
        # запускаем как модуль, чтобы относительный импорт заработал
        start_service "notifications_service" "$BACKEND_DIR/notifications_service" "python main.py"
        sleep 2
    fi
    # Запуск сервиса доставки
    if [ -d "$BACKEND_DIR/delivery_service" ]; then
        # запускаем как модуль, чтобы относительный импорт заработал
        start_service "delivery_service" "$BACKEND_DIR/delivery_service" "python main.py"
        sleep 2
    fi
    # Запуск сервиса избранных
    if [ -d "$BACKEND_DIR/favorite_service" ]; then
        start_service "favorite_service" "$BACKEND_DIR/favorite_service" "python main.py"
        sleep 2
    fi
    
    # Деактивация виртуального окружения не требуется, т.к. каждый сервис запускается в своем подпроцессе
else
    print_message "${YELLOW}[WARNING]${NC} Директория бэкенда не найдена. Бэкенд-сервисы не будут запущены."
fi

echo ""

# Запуск фронтенд-сервиса
print_message "${BLUE}=== ЗАПУСК ФРОНТЕНДА ===${NC}"

# Проверяем наличие директории frontend
if check_directory "$FRONTEND_DIR"; then
    print_message "Директория фронтенда найдена: $FRONTEND_DIR"
    
    # Запуск React-приложения
    start_service "frontend" "$FRONTEND_DIR" "npm start"
else
    print_message "${YELLOW}[WARNING]${NC} Директория фронтенда не найдена. Фронтенд не будет запущен."
fi

echo ""
print_message "${GREEN}Все сервисы запущены!${NC}"
print_message "Логи доступны в директории: ${YELLOW}$LOGS_DIR${NC}"
print_message "Мониторинг Celery доступен по адресу: ${YELLOW}http://localhost:5555${NC}"
print_message "${YELLOW}Для остановки всех сервисов нажмите Ctrl+C${NC}"
echo ""

wait  # wait for all background services to finish 