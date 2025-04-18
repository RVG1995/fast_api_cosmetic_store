import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select

from .config import (
    RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS,
    EVENT_EXCHANGE, EVENT_ROUTING_KEYS,
    SPAM_THRESHOLD, PUSH_QUEUE,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM,
    DLX_NAME, DLX_QUEUE, RETRY_DELAY_MS,
    MAX_RECONNECT_ATTEMPTS, INITIAL_RECONNECT_DELAY, MAX_RECONNECT_DELAY,
    CONNECTION_CHECK_INTERVAL
)
from .database import AsyncSessionLocal
from .models import NotificationSetting, SentNotification

logger = logging.getLogger(__name__)

async def send_email(recipient: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASS,
        use_tls=True
    )

# Функция для создания темы и текста письма на основе данных события
def create_email_content(event_type: str, data: dict) -> tuple:
    """
    Создает тему и текст письма на основе типа события и данных
    
    Args:
        event_type: Тип события
        data: Данные события
        
    Returns:
        Кортеж (тема, текст)
    """
    if event_type == "order.created":
        subject = f"Ваш заказ №{data.get('order_number', 'N/A')} успешно создан"
        
        # Формируем список товаров
        items_text = ""
        for item in data.get('items', []):
            items_text += f"- {item.get('product_name', 'Товар')} x{item.get('quantity', 1)} - {item.get('total_price', 0)} руб.\n"
        
        # Формируем информацию о скидке
        discount_text = ""
        if data.get('discount_amount', 0) > 0:
            promo_info = ""
            if data.get('promo_code'):
                promo_info = f" (промокод {data.get('promo_code', {}).get('code', '')})"
            discount_text = f"\nПрименена скидка{promo_info}: {data.get('discount_amount', 0)} руб."
            
        # Формируем текст письма
        body = f"""Здравствуйте, {data.get('full_name', 'Уважаемый клиент')}!

Ваш заказ №{data.get('order_number', 'N/A')} от {data.get('created_at', 'сегодня')} успешно создан.

Статус заказа: {data.get('status', 'В обработке')}

Товары в заказе:
{items_text}

Общая сумма: {data.get('total_price', 0)} руб.{discount_text}

Данные доставки:
Адрес: {data.get('region', '')}, {data.get('city', '')}, {data.get('street', '')}
Телефон: {data.get('phone', '')}

Спасибо за ваш заказ!
"""
        return subject, body
        
    elif event_type == "order.status_changed":
        subject = f"Статус заказа №{data.get('order_number', 'N/A')} изменен"
        body = f"""Здравствуйте, {data.get('full_name', 'Уважаемый клиент')}!

Статус вашего заказа №{data.get('order_number', 'N/A')} изменен на "{data.get('status', 'Неизвестно')}".

Общая сумма заказа: {data.get('total_price', 0)} руб.

Если у вас возникли вопросы, пожалуйста, свяжитесь с нами.

С уважением,
Команда магазина
"""
        return subject, body
        
    elif event_type == "review.created":
        subject = "Новый отзыв на ваш товар"
        body = f"""Уведомляем вас о новом отзыве:

Автор: {data.get('author', 'Неизвестно')}
Рейтинг: {data.get('rating', '?')}/5
Комментарий: {data.get('comment', 'Без комментария')}

"""
        return subject, body
        
    elif event_type == "review.reply":
        subject = "Ответ на ваш отзыв"
        body = f"""Здравствуйте!

На ваш отзыв был получен ответ:

Ваш отзыв: {data.get('original_comment', 'Не указан')}
Ответ: {data.get('reply', 'Не указан')}

"""
        return subject, body
    
    # Для неизвестных типов событий
    return f"Уведомление: {event_type}", json.dumps(data, indent=2, ensure_ascii=False)

async def process_message(message: aio_pika.IncomingMessage) -> None:
    logger.info(f"[process_message] Received message: routing_key={message.routing_key}, delivery_tag={message.delivery_tag}")
    try:
        body_str = message.body.decode()
        logger.debug(f"[process_message] Raw body: {body_str}")
    except Exception:
        logger.warning("[process_message] Failed to decode message body")
    async with message.process():
        logger.info(f"[process_message] Message acknowledged, handling event")
        event_type = message.routing_key
        logger.info(f"[process_message] Event type: {event_type}")
        try:
            body = json.loads(message.body.decode())
        except json.JSONDecodeError:
            logger.error("[process_message] Invalid JSON payload")
            return
        
        # Проверяем тип события из тела сообщения (используем его, если есть)
        event_type_from_body = body.get("event_type")
        if event_type_from_body:
            event_type = event_type_from_body
            logger.info(f"[process_message] Using event_type from message body: {event_type}")
            
        event_id = body.get("event_id") or body.get("id") or body.get("order_number") or ""
        logger.info(f"[process_message] Event ID: {event_id or '<none>'}")
        
        # Email получателя из сообщения, если есть
        recipient_email = body.get("email")
        
        async with AsyncSessionLocal() as session:
            # Получаем настройки для этого типа события
            search_event_types = [event_type]
            
            # Обрабатываем специальный случай несоответствия между order.status_changed и order.status_change
            if event_type == "order.status_changed":
                search_event_types.append("order.status_change")
            elif event_type == "order.status_change":
                search_event_types.append("order.status_changed")
                
            settings = []
            for search_event_type in search_event_types:
                result = await session.execute(
                    select(NotificationSetting).where(NotificationSetting.event_type == search_event_type)
                )
                type_settings = result.scalars().all()
                settings.extend(type_settings)
                logger.info(f"[process_message] Found {len(type_settings)} settings for event_type={search_event_type}")
            
            logger.info(f"[process_message] Found total {len(settings)} settings")
            
            # Если есть конкретный email в сообщении и нет настроек, создаем временные настройки
            # для события order.created и order.status_changed
            if recipient_email and len(settings) == 0 and event_type in ["order.created", "order.status_changed"]:
                logger.info(f"[process_message] Using recipient email from message: {recipient_email}")
                
                # Проверяем, нет ли явно отключенных настроек для пользователя
                user_id = body.get("user_id")
                should_create_temp_setting = True
                
                if user_id and event_type == "order.status_changed":
                    # Проверяем настройки пользователя
                    user_settings_result = await session.execute(
                        select(NotificationSetting).where(
                            NotificationSetting.user_id == str(user_id),
                            NotificationSetting.event_type == event_type
                        )
                    )
                    user_setting = user_settings_result.scalars().first()
                    
                    # Если пользователь явно отключил email для этого типа события, не отправляем
                    if user_setting and not user_setting.email_enabled:
                        logger.info(f"[process_message] Skip: user={user_id} explicitly disabled email for {event_type}")
                        should_create_temp_setting = False
                
                # Создаем временную настройку с email из сообщения только если не отключено
                if should_create_temp_setting:
                    temp_setting = {
                        "user_id": "guest" if not user_id else str(user_id),
                        "email": recipient_email,
                        "email_enabled": True,
                        "push_enabled": False
                    }
                    settings = [temp_setting]
            
            for setting in settings:
                skip = False
                user_id = setting["user_id"] if isinstance(setting, dict) else setting.user_id
                
                # Проверяем, не отправлялось ли уже уведомление
                if event_id:
                    exists = await session.execute(
                        select(SentNotification).where(
                            SentNotification.user_id == user_id,
                            SentNotification.event_type == event_type,
                            SentNotification.event_id == event_id
                        )
                    )
                    if exists.scalars().first():
                        logger.info(f"[process_message] Skip: notification already sent for user={user_id}, event_id={event_id}")
                        skip = True
                else:
                    # Проверяем, не слишком ли часто отправляются уведомления
                    last = await session.execute(
                        select(SentNotification).where(
                            SentNotification.user_id == user_id,
                            SentNotification.event_type == event_type
                        ).order_by(SentNotification.sent_at.desc()).limit(1)
                    )
                    last_sent = last.scalars().first()
                    if last_sent and (datetime.now(timezone.utc) - last_sent.sent_at).total_seconds() < SPAM_THRESHOLD:
                        logger.info(f"[process_message] Skip: spam threshold not met for user={user_id}")
                        skip = True
                
                if skip:
                    continue
                
                # Получаем настройки email и push
                email_enabled = setting["email_enabled"] if isinstance(setting, dict) else setting.email_enabled
                push_enabled = setting["push_enabled"] if isinstance(setting, dict) else setting.push_enabled
                email = setting["email"] if isinstance(setting, dict) else setting.email
                
                # Отправляем email, если включено
                if email_enabled and email:
                    logger.info(f"[process_message] Sending email to {email} for user={user_id}")
                    # Создаем тему и текст письма на основе типа события и данных
                    subject, body_text = create_email_content(event_type, body)
                    try:
                        await send_email(email, subject, body_text)
                        logger.info(f"[process_message] Email sent to {email} for event_type={event_type}")
                    except Exception as e:
                        logger.error(f"[process_message] Failed to send email: {str(e)}")
                
                # Отправляем push, если включено
                if push_enabled:
                    logger.info(f"[process_message] Publishing push notification for user={user_id}")
                    payload = {"user_id": user_id, "event_type": event_type, "data": body}
                    await message.channel.default_exchange.publish(
                        aio_pika.Message(body=json.dumps(payload).encode()),
                        routing_key=PUSH_QUEUE
                    )
                
                # Записываем в базу информацию об отправленном уведомлении
                if not isinstance(setting, dict):  # Только для реальных пользователей, не для временных настроек
                    session.add(SentNotification(user_id=user_id, event_type=event_type, event_id=event_id or ""))
            
            # Сохраняем изменения в базу
            await session.commit()
            logger.info(f"[process_message] Committed session for event_type={event_type}")

# Функция для обработки сообщений из очереди email_message
async def process_email_message(message: aio_pika.IncomingMessage) -> None:
    logger.info(f"[process_email_message] Received message: delivery_tag={message.delivery_tag}")
    try:
        body_str = message.body.decode()
        logger.debug(f"[process_email_message] Raw body: {body_str}")
    except Exception:
        logger.warning("[process_email_message] Failed to decode message body")
    
    async with message.process():
        try:
            # Парсим JSON
            data = json.loads(message.body.decode())
            
            # Получаем тип события и email получателя
            event_type = data.get("event_type", "order.created")
            recipient_email = data.get("email")
            
            if not recipient_email:
                logger.error("[process_email_message] No recipient email in message")
                return
                
            # Создаем тему и текст письма
            subject, body_text = create_email_content(event_type, data)
            
            # Отправляем email
            logger.info(f"[process_email_message] Sending email to {recipient_email}")
            await send_email(recipient_email, subject, body_text)
            logger.info(f"[process_email_message] Email sent to {recipient_email}")
            
            # Записываем информацию об отправке в базу
            async with AsyncSessionLocal() as session:
                # Используем "guest" как ID пользователя для гостевых заказов
                user_id = data.get("user_id", "guest")
                event_id = data.get("order_number", "")
                
                session.add(SentNotification(
                    user_id=user_id, 
                    event_type=event_type, 
                    event_id=event_id
                ))
                await session.commit()
                
        except Exception as e:
            logger.error(f"[process_email_message] Error processing message: {str(e)}")
            # В случае ошибки сообщение уже будет обработано из-за async with message.process()

# Функция для обработки сообщений из очереди update_message
async def process_update_message(message: aio_pika.IncomingMessage) -> None:
    logger.info(f"[process_update_message] Received message: delivery_tag={message.delivery_tag}")
    try:
        body_str = message.body.decode()
        logger.debug(f"[process_update_message] Raw body: {body_str}")
    except Exception:
        logger.warning("[process_update_message] Failed to decode message body")
    
    async with message.process():
        try:
            # Парсим JSON
            data = json.loads(message.body.decode())
            
            # Получаем тип события и email получателя
            event_type = data.get("event_type", "order.status_changed")
            recipient_email = data.get("email")
            
            if not recipient_email:
                logger.error("[process_update_message] No recipient email in message")
                return
                
            # Создаем тему и текст письма
            subject, body_text = create_email_content(event_type, data)
            
            # Отправляем email
            logger.info(f"[process_update_message] Sending email to {recipient_email}")
            await send_email(recipient_email, subject, body_text)
            logger.info(f"[process_update_message] Email sent to {recipient_email}")
            
            # Записываем информацию об отправке в базу
            async with AsyncSessionLocal() as session:
                # Используем "guest" как ID пользователя для гостевых заказов
                user_id = data.get("user_id", "guest")
                event_id = data.get("order_number", "")
                
                session.add(SentNotification(
                    user_id=user_id, 
                    event_type=event_type, 
                    event_id=event_id
                ))
                await session.commit()
                
        except Exception as e:
            logger.error(f"[process_update_message] Error processing message: {str(e)}")
            # В случае ошибки сообщение уже будет обработано из-за async with message.process()

class RabbitMQConsumer:
    """Класс управления подключением и потреблением сообщений из RabbitMQ"""
    def __init__(self, handlers):
        self.handlers = handlers
        self.connection = None
        self.channel = None
        self.is_running = False
        self.check_task = None
        self._future = None

    async def get_connection_with_retry(self):
        delay = INITIAL_RECONNECT_DELAY
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            try:
                conn = await aio_pika.connect_robust(
                    host=RABBITMQ_HOST,
                    login=RABBITMQ_USER,
                    password=RABBITMQ_PASS
                )
                logger.info("RabbitMQ connected")
                return conn
            except Exception as e:
                logger.error(f"Connection attempt {attempt} failed: {e}")
                if attempt == MAX_RECONNECT_ATTEMPTS:
                    raise
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RECONNECT_DELAY)

    async def setup(self):
        self.connection = await self.get_connection_with_retry()
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)

    async def _setup_consumers(self):
        dlx = await self.channel.declare_exchange(DLX_NAME, aio_pika.ExchangeType.DIRECT, durable=True)
        failed_q = await self.channel.declare_queue(DLX_QUEUE, durable=True)
        await failed_q.bind(dlx, routing_key="#")
        for q_name, handler in self.handlers.items():
            # retry queue
            await self.channel.declare_queue(
                f"{q_name}.retry", durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": q_name,
                    "x-message-ttl": RETRY_DELAY_MS
                }
            )
            # main queue
            queue = await self.channel.declare_queue(
                q_name, durable=True,
                arguments={
                    "x-dead-letter-exchange": DLX_NAME,
                    "x-dead-letter-routing-key": q_name
                }
            )
            await queue.consume(handler)
            logger.info(f"Consumer set for {q_name}")

    async def check_connection(self):
        while self.is_running:
            try:
                if self.connection and self.connection.is_closed:
                    logger.warning("Connection closed, reconnecting...")
                    await self._reconnect()
                await asyncio.sleep(CONNECTION_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection check error: {e}")

    async def _reconnect(self):
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            await self.setup()
            await self._setup_consumers()
            logger.info("Reconnected to RabbitMQ")
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")

    async def start(self):
        self.is_running = True
        await self.setup()
        await self._setup_consumers()
        self.check_task = asyncio.create_task(self.check_connection())
        self._future = asyncio.Future()
        try:
            await self._future
        except asyncio.CancelledError:
            self.is_running = False

    async def stop(self):
        self.is_running = False
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        if self._future and not self._future.done():
            self._future.cancel()
            try:
                await self._future
            except asyncio.CancelledError:
                pass
        if self.connection:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

async def start_consumer() -> RabbitMQConsumer:
    """Initialize consumer: setup queues and start connection check in background"""
    # Обработчики для разных очередей
    handlers = {
        "notification_events": process_message,   # Очередь для общих уведомлений
        "email_message": process_email_message,   # Очередь для сообщений о создании заказа
        "update_message": process_update_message  # Очередь для сообщений об изменении статуса
    }
    
    consumer = RabbitMQConsumer(handlers)
    # Setup connection and queues
    await consumer.setup()
    await consumer._setup_consumers()
    # Start periodic connection checker
    consumer.check_task = asyncio.create_task(consumer.check_connection())
    return consumer

#async def main() -> None:
#    consumer = RabbitMQConsumer(QUEUE_HANDLERS)
#    
#    try:
#        await consumer.start()
#    except KeyboardInterrupt:
#        logger.info("Получен сигнал остановки")
#    except Exception as e:
#        logger.error(f"Критическая ошибка: {e}")
#    finally:
#        await consumer.stop()
#
#
#if __name__ == "__main__":
#    try:
#        asyncio.run(main())
#    except KeyboardInterrupt:
#        logger.info("Consumer остановлен пользователем") 