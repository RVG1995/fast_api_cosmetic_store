from celery_app import app
from sqlalchemy import select, func
from models import CartModel, Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import os
import asyncio
from dotenv import load_dotenv
import pathlib

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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/cart_db")

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
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

async def delete_old_anonymous_carts_async(days: int = 1):
    """
    Асинхронная функция для удаления устаревших анонимных корзин.
    
    Args:
        days: Количество дней с момента последнего обновления, после которого корзина считается устаревшей
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    logger.info(f"Удаление анонимных корзин, не обновлявшихся с {cutoff_date}")
    
    try:
        async with AsyncSessionLocal() as session:
            # Выбираем анонимные корзины (с session_id, но без user_id), 
            # которые не обновлялись более указанного времени
            query = select(CartModel).filter(
                CartModel.user_id == None,  # Только анонимные корзины
                CartModel.session_id != None,  # С указанным session_id
                CartModel.updated_at < cutoff_date  # Не обновлялись в указанный период
            )
            
            result = await session.execute(query)
            carts_to_delete = result.scalars().all()
            
            if not carts_to_delete:
                logger.info("Не найдено устаревших анонимных корзин для удаления")
                return 0
            
            deleted_count = 0
            for cart in carts_to_delete:
                logger.info(f"Удаление корзины ID {cart.id}, session_id: {cart.session_id}, последнее обновление: {cart.updated_at}")
                await session.delete(cart)
                deleted_count += 1
            
            await session.commit()
            logger.info(f"Удалено устаревших анонимных корзин: {deleted_count}")
            return deleted_count
            
    except Exception as e:
        logger.error(f"Ошибка при удалении устаревших корзин: {str(e)}")
        return 0

@app.task(name="tasks.cleanup_old_anonymous_carts")
def cleanup_old_anonymous_carts(days: int = 1):
    """
    Celery-задача для удаления устаревших анонимных корзин.
    
    Args:
        days: Количество дней с момента последнего обновления, после которого корзина считается устаревшей
    """
    logger.info(f"Запуск задачи очистки устаревших анонимных корзин старше {days} дней")
    
    try:
        # Запускаем асинхронную функцию в синхронном контексте Celery
        deleted_count = run_async(delete_old_anonymous_carts_async(days))
        logger.info(f"Задача очистки завершена. Удалено корзин: {deleted_count}")
        return deleted_count
    except Exception as e:
        logger.error(f"Ошибка в задаче очистки корзин: {str(e)}")
        return 0 