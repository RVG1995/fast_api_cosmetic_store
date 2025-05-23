"""Модуль для работы с базой данных корзины."""
from typing import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base
from config import settings, get_db_url

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_database")

# Получаем URL подключения к базе данных из конфигурации
DATABASE_URL = get_db_url()
logger.info("URL базы данных: %s", DATABASE_URL)

# Создаем движок SQLAlchemy для асинхронной работы с базой данных
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,  # Вывод SQL-запросов в консоль
)

# Создаем асинхронную фабрику сессий
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False  # Чтобы объекты не истекали после commit
)

async def setup_database():
    """Создает все таблицы в базе данных"""
    logger.info("Создание таблиц в базе данных...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы успешно созданы")
    except Exception as e:
        logger.error("Ошибка при создании таблиц: %s", str(e))
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет асинхронную сессию базы данных"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Ошибка при работе с базой данных: %s", str(e))
            await session.rollback()
            raise
        finally:
            await session.close() 