#!/bin/bash

# Скрипт для остановки всех сервисов магазина косметики
# Автор: Claude AI

# Установка цветов для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Директория проекта (текущая директория)
PROJECT_DIR=$(pwd)
LOGS_DIR="$PROJECT_DIR/logs"

# Функция для вывода сообщений
print_message() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

# Информация о скрипте
print_message "${BLUE}========================================${NC}"
print_message "${BLUE}   ОСТАНОВКА СЕРВИСОВ КОСМЕТИК-СТОР   ${NC}"
print_message "${BLUE}========================================${NC}"

# Проверяем наличие директории с логами
if [ ! -d "$LOGS_DIR" ]; then
    print_message "${RED}[ERROR]${NC} Директория логов $LOGS_DIR не существует!"
    print_message "${YELLOW}Возможно, сервисы не были запущены через скрипт start_services.sh${NC}"
    
    # Пытаемся остановить процессы по имени (запасной вариант)
    print_message "${YELLOW}Попытка найти и остановить процессы uvicorn и node...${NC}"
    
    # Находим процессы uvicorn
    UVICORN_PIDS=$(pgrep -f "uvicorn main:app")
    if [ -n "$UVICORN_PIDS" ]; then
        print_message "Найдены процессы uvicorn: $UVICORN_PIDS"
        for pid in $UVICORN_PIDS; do
            echo -e "Остановка процесса с PID $pid..."
            kill -15 $pid 2>/dev/null
            sleep 1
            if ps -p $pid > /dev/null; then
                echo -e "${RED}Принудительная остановка процесса с PID $pid...${NC}"
                kill -9 $pid 2>/dev/null
            fi
        done
    else
        print_message "Процессы uvicorn не найдены"
    fi
    
    # Находим процессы node (React)
    NODE_PIDS=$(pgrep -f "node.*react-scripts start")
    if [ -n "$NODE_PIDS" ]; then
        print_message "Найдены процессы node (React): $NODE_PIDS"
        for pid in $NODE_PIDS; do
            echo -e "Остановка процесса с PID $pid..."
            kill -15 $pid 2>/dev/null
            sleep 1
            if ps -p $pid > /dev/null; then
                echo -e "${RED}Принудительная остановка процесса с PID $pid...${NC}"
                kill -9 $pid 2>/dev/null
            fi
        done
    else
        print_message "Процессы node (React) не найдены"
    fi
    
    print_message "${GREEN}Процесс остановки завершен${NC}"
    exit 0
fi

# Проверяем наличие файлов PID
PID_FILES=$(find "$LOGS_DIR" -name "*.pid" -type f 2>/dev/null)
if [ -z "$PID_FILES" ]; then
    print_message "${YELLOW}[WARNING]${NC} Не найдены PID-файлы запущенных сервисов."
    print_message "${YELLOW}Возможно, сервисы не запущены или были запущены не через скрипт start_services.sh${NC}"
    
    # Пытаемся остановить процессы по имени (запасной вариант)
    print_message "${YELLOW}Попытка найти и остановить процессы uvicorn и node...${NC}"
    
    # Находим процессы uvicorn
    UVICORN_PIDS=$(pgrep -f "uvicorn main:app")
    if [ -n "$UVICORN_PIDS" ]; then
        print_message "Найдены процессы uvicorn: $UVICORN_PIDS"
        for pid in $UVICORN_PIDS; do
            echo -e "Остановка процесса с PID $pid..."
            kill -15 $pid 2>/dev/null
            sleep 1
            if ps -p $pid > /dev/null; then
                echo -e "${RED}Принудительная остановка процесса с PID $pid...${NC}"
                kill -9 $pid 2>/dev/null
            fi
        done
    else
        print_message "Процессы uvicorn не найдены"
    fi
    
    # Находим процессы node (React)
    NODE_PIDS=$(pgrep -f "node.*react-scripts start")
    if [ -n "$NODE_PIDS" ]; then
        print_message "Найдены процессы node (React): $NODE_PIDS"
        for pid in $NODE_PIDS; do
            echo -e "Остановка процесса с PID $pid..."
            kill -15 $pid 2>/dev/null
            sleep 1
            if ps -p $pid > /dev/null; then
                echo -e "${RED}Принудительная остановка процесса с PID $pid...${NC}"
                kill -9 $pid 2>/dev/null
            fi
        done
    else
        print_message "Процессы node (React) не найдены"
    fi
    
    print_message "${GREEN}Процесс остановки завершен${NC}"
    exit 0
fi

print_message "${YELLOW}Остановка всех сервисов...${NC}"

# Останавливаем все процессы
COUNT_STOPPED=0
for pid_file in "$LOGS_DIR"/*.pid; do
    if [ -f "$pid_file" ]; then
        service_name=$(basename "$pid_file" .pid)
        pid=$(cat "$pid_file")
        
        print_message "Остановка сервиса $service_name (PID: $pid)..."
        if ! ps -p "$pid" > /dev/null; then
            echo -e "${YELLOW}[WARNING]${NC} Процесс с PID $pid уже не существует"
            rm -f "$pid_file"
            continue
        fi
        
        # Пробуем мягкую остановку
        kill -15 "$pid" 2>/dev/null
        
        # Ждем немного и проверяем, остановился ли процесс
        ATTEMPT=0
        MAX_ATTEMPTS=5
        while ps -p "$pid" > /dev/null && [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
            echo -e "${YELLOW}Ожидание завершения сервиса $service_name...${NC}"
            sleep 1
            ATTEMPT=$((ATTEMPT + 1))
        done
        
        # Если процесс не остановился, принудительно завершаем его
        if ps -p "$pid" > /dev/null; then
            echo -e "${RED}[WARNING]${NC} Сервис $service_name не отвечает. Принудительное завершение..."
            kill -9 "$pid" 2>/dev/null
            
            sleep 1
            if ! ps -p "$pid" > /dev/null; then
                echo -e "${GREEN}[OK]${NC} Сервис $service_name принудительно остановлен"
                COUNT_STOPPED=$((COUNT_STOPPED + 1))
            else
                echo -e "${RED}[ERROR]${NC} Не удалось остановить сервис $service_name!"
            fi
        else
            echo -e "${GREEN}[OK]${NC} Сервис $service_name остановлен"
            COUNT_STOPPED=$((COUNT_STOPPED + 1))
        fi
        
        # Удаляем PID-файл
        rm -f "$pid_file"
    fi
done

# Проверяем, остались ли какие-то процессы uvicorn или node, которые нужно остановить
print_message "${YELLOW}Проверка наличия оставшихся процессов...${NC}"

# Находим процессы uvicorn
UVICORN_PIDS=$(pgrep -f "uvicorn main:app")
if [ -n "$UVICORN_PIDS" ]; then
    print_message "Найдены оставшиеся процессы uvicorn: $UVICORN_PIDS"
    for pid in $UVICORN_PIDS; do
        echo -e "Остановка процесса с PID $pid..."
        kill -15 $pid 2>/dev/null
        sleep 1
        if ps -p $pid > /dev/null; then
            echo -e "${RED}Принудительная остановка процесса с PID $pid...${NC}"
            kill -9 $pid 2>/dev/null
            COUNT_STOPPED=$((COUNT_STOPPED + 1))
        else
            COUNT_STOPPED=$((COUNT_STOPPED + 1))
        fi
    done
fi

# Находим процессы node (React)
NODE_PIDS=$(pgrep -f "node.*react-scripts start")
if [ -n "$NODE_PIDS" ]; then
    print_message "Найдены оставшиеся процессы node (React): $NODE_PIDS"
    for pid in $NODE_PIDS; do
        echo -e "Остановка процесса с PID $pid..."
        kill -15 $pid 2>/dev/null
        sleep 1
        if ps -p $pid > /dev/null; then
            echo -e "${RED}Принудительная остановка процесса с PID $pid...${NC}"
            kill -9 $pid 2>/dev/null
            COUNT_STOPPED=$((COUNT_STOPPED + 1))
        else
            COUNT_STOPPED=$((COUNT_STOPPED + 1))
        fi
    done
fi

if [ $COUNT_STOPPED -gt 0 ]; then
    print_message "${GREEN}Все сервисы остановлены ($COUNT_STOPPED)${NC}"
else
    print_message "${YELLOW}Ни один сервис не был остановлен${NC}"
fi

print_message "${GREEN}Готово!${NC}"
exit 0 