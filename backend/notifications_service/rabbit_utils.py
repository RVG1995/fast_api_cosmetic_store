"""Утилиты для работы с RabbitMQ в сервисе уведомлений."""

import aio_pika

from .config import settings

# Настройки получаем из settings объекта
async def get_connection() -> aio_pika.Connection:
    """Создает подключение к RabbitMQ"""
    connection = await aio_pika.connect_robust(
        host=settings.RABBITMQ_HOST,
        login=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASS
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
                "x-dead-letter-exchange": settings.DLX_NAME,
                "x-dead-letter-routing-key": queue_name
            }
        )
        return queue
    except aio_pika.exceptions.ChannelInvalidStateError as e:
        # Если очередь уже существует, используем её как есть
        # (это может произойти, если email_consumer уже создал очереди)
        print(f"Очередь {queue_name} уже существует с другими параметрами. Используем как есть: {e}")
        queue = await channel.declare_queue(
            queue_name,
            passive=True  # Только проверяем существование, не меняем настройки
        )
        return queue
