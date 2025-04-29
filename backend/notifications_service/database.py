"""Модуль настройки асинхронного подключения к БД и генерации сессий."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import DATABASE_URL

# Создаем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем сессию
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Базовый класс моделей
Base = declarative_base()

async def get_db():
    """Генератор для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        yield session
