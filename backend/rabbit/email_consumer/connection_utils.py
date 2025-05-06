"""
Утилиты для работы с соединением к RabbitMQ
"""
import asyncio

import aio_pika

from config import (
    RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS,
    MAX_RECONNECT_ATTEMPTS, INITIAL_RECONNECT_DELAY, MAX_RECONNECT_DELAY,
    logger
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
    reconnect_delay = INITIAL_RECONNECT_DELAY
    attempts = 0
    
    while attempts < MAX_RECONNECT_ATTEMPTS:
        try:
            connection = await aio_pika.connect_robust(
                host=RABBITMQ_HOST,
                login=RABBITMQ_USER,
                password=RABBITMQ_PASS
            )
            logger.info("Соединение с RabbitMQ установлено успешно")
            return connection
        except (aio_pika.exceptions.AMQPException, OSError) as e:
            attempts += 1
            logger.error("Ошибка подключения к RabbitMQ (%d/%d): %s", attempts, MAX_RECONNECT_ATTEMPTS, e)
            
            if attempts >= MAX_RECONNECT_ATTEMPTS:
                logger.critical("Превышено максимальное количество попыток подключения")
                raise
            
            logger.info("Повторная попытка через %d сек...", reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            
            # Экспоненциальное увеличение задержки с ограничением
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY) 