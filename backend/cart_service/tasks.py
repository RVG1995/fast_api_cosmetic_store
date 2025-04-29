"""Задачи Celery для операций с корзиной, включая очистку старых анонимных корзин."""

import asyncio
import logging
import os
import pathlib
from datetime import datetime, timedelta

from celery_app import app
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import CartModel, Base
from sqlalchemy.exc import SQLAlchemyError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_tasks")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    load_dotenv(dotenv_path=parent_env_file)

# Получаем URL подключения к базе данных из переменных окружения
DATABASE_URL = os.getenv(
    "DATABASE_URL",
     "postgresql+asyncpg://postgres:postgres@localhost:5434/cart_db")

# Создаем движок SQLAlchemy для асинхронной работы с базой данных
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
)

# Создаем асинхронную фабрику сессий
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Обертка для запуска асинхронных функций внутри задач Celery
def run_async(coro):
    """Запускает асинхронную корутину в синхронном контексте."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

async def delete_old_anonymous_carts_async(days: int = 1):
    """
    Асинхронная функция для удаления устаревших анонимных корзин.
    
    Args:
        days: Количество дней с момента последнего обновления, после которого корзина считается устаревшей
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    logger.info("Удаление анонимных корзин, не обновлявшихся с %s", cutoff_date)
    
    try:
        async with AsyncSessionLocal() as session:
            # Выбираем анонимные корзины (с session_id, но без user_id), 
            # которые не обновлялись более указанного времени
            query = select(CartModel).filter(
                CartModel.user_id is None,  # Только анонимные корзины
                CartModel.session_id is not None,  # С указанным session_id
                CartModel.updated_at < cutoff_date  # Не обновлялись в указанный период
            )
            
            result = await session.execute(query)
            carts_to_delete = result.scalars().all()
            
            if not carts_to_delete:
                logger.info("Не найдено устаревших анонимных корзин для удаления")
                return 0
            
            deleted_count = 0
            for cart in carts_to_delete:
                logger.info("Удаление корзины ID %s, session_id: %s, последнее обновление: %s", 
                          cart.id, cart.session_id, cart.updated_at)
                await session.delete(cart)
                deleted_count += 1
            
            await session.commit()
            logger.info("Удалено устаревших анонимных корзин: %s", deleted_count)
            return deleted_count
            
    except SQLAlchemyError as e:
        logger.error("Ошибка при удалении устаревших корзин: %s", str(e))
        return 0

@app.task(name="tasks.cleanup_old_anonymous_carts")
def cleanup_old_anonymous_carts(days: int = 1):
    """
    Celery-задача для удаления устаревших анонимных корзин.
    
    Args:
        days: Количество дней с момента последнего обновления, после которого корзина считается устаревшей
    """
    logger.info("Запуск задачи очистки устаревших анонимных корзин старше %s дней", days)
    
    try:
        # Запускаем асинхронную функцию в синхронном контексте Celery
        deleted_count = run_async(delete_old_anonymous_carts_async(days))
        logger.info("Задача очистки завершена. Удалено корзин: %s", deleted_count)
        return deleted_count
    except (SQLAlchemyError, RuntimeError) as e:
        logger.error("Ошибка в задаче очистки корзин: %s", str(e))
        return 0 