"""
Утилиты для работы с соединением к RabbitMQ
"""
import asyncio

import aio_pika

from config import (
    settings, get_rabbitmq_url, logger
)


async def close_connection(connection: aio_pika.Connection) -> None:
    """
    Закрывает соединение с RabbitMQ
    
    Args:
        connection: Соединение с RabbitMQ для закрытия
    """
    if connection and not connection.is_closed:
        await connection.close()
        logger.info("Соединение с RabbitMQ закрыто")


async def get_connection_with_retry() -> aio_pika.Connection:
    """
    Устанавливает соединение с RabbitMQ с механизмом повторных попыток
    при неудаче
    
    Returns:
        aio_pika.Connection: Установленное соединение
    """
    reconnect_delay = settings.INITIAL_RECONNECT_DELAY
    attempts = 0
    
    while attempts < settings.MAX_RECONNECT_ATTEMPTS:
        try:
            # Используем функцию get_rabbitmq_url для получения URL подключения
            rabbitmq_url = get_rabbitmq_url()
            connection = await aio_pika.connect_robust(
                rabbitmq_url
            )
            logger.info("Соединение с RabbitMQ установлено успешно")
            return connection
        except (aio_pika.exceptions.AMQPException, OSError) as e:
            attempts += 1
            logger.error("Ошибка подключения к RabbitMQ (%d/%d): %s", attempts, settings.MAX_RECONNECT_ATTEMPTS, e)
            
            if attempts >= settings.MAX_RECONNECT_ATTEMPTS:
                logger.critical("Превышено максимальное количество попыток подключения")
                raise
            
            logger.info("Повторная попытка через %d сек...", reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            
            # Экспоненциальное увеличение задержки с ограничением
            reconnect_delay = min(reconnect_delay * 2, settings.MAX_RECONNECT_DELAY) 