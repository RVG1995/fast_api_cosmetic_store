"""Конфигурация сервиса уведомлений."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RabbitMQ settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
EVENT_EXCHANGE = os.getenv("EVENT_EXCHANGE", "events")
EVENT_ROUTING_KEYS = os.getenv(
    "EVENT_ROUTING_KEYS", 
    "review.created,review.reply,service.critical_error,order.created,order.status_changed,product.low_stock"
).split(",")

# Database settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5437/notifications_db"
)

# Spam prevention threshold (seconds)
SPAM_THRESHOLD = int(os.getenv("SPAM_THRESHOLD", "300"))

# SMTP settings
SMTP_HOST = os.getenv("MAIL_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("MAIL_PORT", "587"))
SMTP_USER = os.getenv("MAIL_USERNAME", "")
SMTP_PASS = os.getenv("MAIL_PASSWORD", "")
SMTP_FROM = os.getenv("MAIL_FROM", "")

# Push notifications queue name
PUSH_QUEUE = os.getenv("PUSH_QUEUE", "push_notifications")

# Auth service settings
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")

# Dead Letter Exchange и retry для очередей уведомлений
DLX_NAME = os.getenv("DLX_NAME", "dead_letter_exchange")
DLX_QUEUE = os.getenv("DLX_QUEUE", "failed_notifications")
MAX_RETRY_COUNT = int(os.getenv("MAX_RETRY_COUNT", "3"))
RETRY_DELAY_MS = int(os.getenv("RETRY_DELAY_MS", "5000"))
# Настройки для реконнекта
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "10"))
INITIAL_RECONNECT_DELAY = float(os.getenv("INITIAL_RECONNECT_DELAY", "1"))
MAX_RECONNECT_DELAY = float(os.getenv("MAX_RECONNECT_DELAY", "30"))
CONNECTION_CHECK_INTERVAL = float(os.getenv("CONNECTION_CHECK_INTERVAL", "5"))

EVENT_TYPE_ORDER_STATUS_CHANGED = "order.status_changed"

# Redis settings for notifications cache
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# TTL for notification settings cache in seconds
SETTINGS_CACHE_TTL = int(os.getenv("NOTIFICATIONS_SETTINGS_CACHE_TTL", "60"))
