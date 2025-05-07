"""Настройки и подключение к базе данных."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings, get_db_url

# Создаем асинхронный движок
engine = create_async_engine(get_db_url(), echo=False)

# Создаем сессию
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Базовый класс моделей
Base = declarative_base()

async def get_db():
    """Генератор для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        yield session 
