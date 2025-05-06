"""
Конфигурация для RabbitMQ email consumer.
"""
import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

# Настройки для Dead Letter Exchange
DLX_NAME = "dead_letter_exchange"
DLX_QUEUE = "failed_messages"
# Максимальное количество попыток обработки сообщения
MAX_RETRY_COUNT = 3
# Задержка перед повторной попыткой в миллисекундах
RETRY_DELAY_MS = 5000

# Настройки SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@example.com")

# Путь к директории с шаблонами
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Настройки для реконнекта
MAX_RECONNECT_ATTEMPTS = 10
INITIAL_RECONNECT_DELAY = 1  # Начальная задержка в секундах
MAX_RECONNECT_DELAY = 30     # Максимальная задержка в секундах
CONNECTION_CHECK_INTERVAL = 5  # Интервал проверки соединения в секундах 