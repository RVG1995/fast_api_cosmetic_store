"""Сервис для отправки email-сообщений через RabbitMQ."""

import json
import logging
import aio_pika
from ..utils.rabbit_utils import get_connection, close_connection, declare_queue

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
        queue = await declare_queue(channel, "registration_message")

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
        logger.info("RabbitMQ: %s", json.dumps(message_body, ensure_ascii=False))
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)

async def send_password_reset_email(user_id: str, email: str, reset_token: str):
    """
    Отправляет сообщение для сброса пароля в очередь
    """
    connection = await get_connection()
    try:
        channel = await connection.channel()
        queue = await declare_queue(channel, "password_reset_message")
        reset_link = f"http://localhost:3000/reset-password/{reset_token}"
        message_body = {
            "user_id": user_id,
            "email": email,
            "reset_link": reset_link
        }
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info("RabbitMQ: %s", json.dumps(message_body, ensure_ascii=False))
    finally:
        await close_connection(connection)
