"""
RabbitMQ consumer для email-уведомлений и обработки очередей (email, регистрация, сброс пароля, уведомления).
"""
import asyncio

from config import logger
from message_handlers import QUEUE_HANDLERS
from consumer_class import RabbitMQConsumer


async def main() -> None:
    """Основная функция для запуска consumer"""
    consumer = RabbitMQConsumer(QUEUE_HANDLERS)
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error("Критическая ошибка: %s", e)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer остановлен пользователем") 