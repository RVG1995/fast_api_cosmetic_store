"""Утилиты для работы с RabbitMQ в сервисе аутентификации."""

import os

import aio_pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

# Настройки для Dead Letter Exchange - должны совпадать с настройками в email_consumer
DLX_NAME = "dead_letter_exchange"
DLX_QUEUE = "failed_messages"
# Задержка перед повторной попыткой в миллисекундах
RETRY_DELAY_MS = 5000


async def get_connection() -> aio_pika.Connection:
    """Создает подключение к RabbitMQ"""
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASS
    )
    return connection


async def close_connection(connection: aio_pika.Connection) -> None:
    """
    Закрывает соединение с RabbitMQ
    
    Args:
        connection: Соединение с RabbitMQ для закрытия
    """
    if connection and not connection.is_closed:
        await connection.close()
        print("Соединение с RabbitMQ закрыто")


async def declare_queue(channel: aio_pika.Channel, queue_name: str) -> aio_pika.Queue:
    """
    Объявляет очередь с поддержкой DLX.
    Используется для объявления очередей согласованно с email_consumer.
    
    Args:
        channel: Канал RabbitMQ
        queue_name: Имя очереди
        
    Returns:
        aio_pika.Queue: Объявленная очередь
    """
    try:
        # Объявляем основную очередь с DLX
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": DLX_NAME,
                "x-dead-letter-routing-key": queue_name
            }
        )
        return queue
    except aio_pika.exceptions.ChannelClosed as e:
        # Если очередь уже существует, используем её как есть
        print(f"Очередь {queue_name} уже существует с другими параметрами. Используем как есть: {e}")
        queue = await channel.declare_queue(
            queue_name,
            passive=True  # Только проверяем существование, не меняем настройки
        )
        return queue
