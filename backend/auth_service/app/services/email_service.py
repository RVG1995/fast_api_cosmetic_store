import logging
from ..utils.rabbit_utils import get_connection, close_connection
import json
import aio_pika

logger = logging.getLogger(__name__)

async def send_email_activation_message(
    user_id: str,
    email: str,
    activation_link: str
):
    """
    Отправляет сообщение с данными для email в очередь
    
    Args:
        user_id: ID пользователя
        email: Email получателя
        activation_link: Ссылка для активации аккаунта
    """
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь
        queue = await channel.declare_queue(
            "registration_message",
            durable=True
        )
        message_body = {
            "user_id": user_id,
            "email": email,
            "activation_link": activation_link
        }
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f"RabbitMQ: {json.dumps(message_body, ensure_ascii=False)}")
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)
