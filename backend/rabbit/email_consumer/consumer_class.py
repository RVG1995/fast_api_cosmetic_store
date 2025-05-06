"""
Класс для управления потреблением сообщений из RabbitMQ
"""
import asyncio
from typing import Dict, Callable, Optional

import aio_pika

from config import (
    DLX_NAME, DLX_QUEUE, CONNECTION_CHECK_INTERVAL, RETRY_DELAY_MS,
    logger
)
from connection_utils import get_connection_with_retry, close_connection


class RabbitMQConsumer:
    """Класс для управления подключением и потреблением сообщений из RabbitMQ"""
    
    def __init__(self, queue_handlers: Dict[str, Callable]):
        """
        Инициализирует consumer
        
        Args:
            queue_handlers: Словарь с именами очередей и их обработчиками
        """
        self.queue_handlers = queue_handlers
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.is_running = False
        self.connection_check_task: Optional[asyncio.Task] = None
        self._running_future: Optional[asyncio.Future] = None
        
    async def setup(self) -> None:
        """Устанавливает соединение и настраивает канал"""
        self.connection = await get_connection_with_retry()
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        
    async def check_connection(self) -> None:
        """Периодически проверяет состояние соединения и восстанавливает его при необходимости"""
        while self.is_running:
            try:
                # Проверяем, работает ли соединение
                if self.connection and self.connection.is_closed:
                    logger.warning("Обнаружено закрытое соединение. Запуск переподключения...")
                    await self._reconnect()
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(CONNECTION_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Ошибка при проверке соединения: %s", e)
                await asyncio.sleep(1)
    
    async def _reconnect(self) -> None:
        """Процедура переподключения при разрыве соединения"""
        try:
            # Закрываем старое соединение, если оно еще открыто
            if self.connection and not self.connection.is_closed:
                await close_connection(self.connection)
                
            # Устанавливаем новое соединение
            await self.setup()
            await self._setup_consumers()
            logger.info("Переподключение выполнено успешно")
        except (aio_pika.exceptions.AMQPException, OSError) as e:
            logger.error("Ошибка при переподключении: %s", e)
    
    async def _setup_consumers(self) -> None:
        """Настраивает потребителей сообщений для всех очередей"""
        try:
            # Создаем Dead Letter Exchange
            dlx = await self.channel.declare_exchange(
                DLX_NAME,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # Создаем очередь для неудачных сообщений
            failed_queue = await self.channel.declare_queue(
                DLX_QUEUE,
                durable=True
            )
            
            # Привязываем очередь к DLX для всех маршрутов
            await failed_queue.bind(dlx, routing_key="#")
            logger.info("Настроен Dead Letter Exchange %s и очередь %s", DLX_NAME, DLX_QUEUE)
            
            # Настраиваем обработчики для основных очередей
            for queue_name, handler in self.queue_handlers.items():
                # Создаем очередь для отложенных сообщений (retry)
                retry_queue_name = f"{queue_name}.retry"
                retry_queue = await self.channel.declare_queue(
                    retry_queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": "",  # Используем default exchange
                        "x-dead-letter-routing-key": queue_name,  # Возвращаем в оригинальную очередь
                        "x-message-ttl": RETRY_DELAY_MS  # Задержка перед повторной попыткой
                    }
                )
                
                # Создаем основную очередь с DLX
                queue = await self.channel.declare_queue(
                    queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": DLX_NAME,
                        "x-dead-letter-routing-key": queue_name
                    }
                )
                
                await queue.consume(handler)
                logger.info("Настроен обработчик для очереди %s с поддержкой DLX", queue_name)
        except (aio_pika.exceptions.AMQPException, OSError) as e:
            logger.error("Ошибка при настройке очередей: %s", e)
            raise
    
    async def start(self) -> None:
        """Запускает consumer"""
        self.is_running = True
        await self.setup()
        await self._setup_consumers()
        
        # Запускаем задачу проверки соединения
        self.connection_check_task = asyncio.create_task(self.check_connection())
        
        logger.info("Consumer запущен. Ожидание сообщений из %d очередей", len(self.queue_handlers))
        
        # Создаем Future, который никогда не завершится, чтобы процесс не завершался
        self._running_future = asyncio.Future()
        try:
            await self._running_future
        except asyncio.CancelledError:
            self.is_running = False
            logger.info("Consumer остановлен")
    
    async def stop(self) -> None:
        """Останавливает consumer"""
        self.is_running = False
        
        # Останавливаем задачу проверки соединения
        if self.connection_check_task and not self.connection_check_task.done():
            self.connection_check_task.cancel()
            try:
                await self.connection_check_task
            except asyncio.CancelledError:
                pass
        
        # Останавливаем основной цикл
        if hasattr(self, '_running_future') and self._running_future and not self._running_future.done():
            self._running_future.cancel()
            try:
                await self._running_future
            except asyncio.CancelledError:
                pass
        
        # Закрываем соединение
        if self.connection:
            await close_connection(self.connection) 