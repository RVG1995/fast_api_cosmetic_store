#!/usr/bin/env python3
"""Миграция: добавляет колонку is_anonymous в таблице reviews"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import asyncpg

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

# Загружаем переменные окружения
load_dotenv()

# Получаем параметры подключения к БД
REVIEW_DB_USER = os.getenv("REVIEW_DB_USER", "postgres")
REVIEW_DB_PASSWORD = os.getenv("REVIEW_DB_PASSWORD", "postgres")
REVIEW_DB_HOST = os.getenv("REVIEW_DB_HOST", "localhost")
REVIEW_DB_PORT = os.getenv("REVIEW_DB_PORT", "5436")
REVIEW_DB_NAME = os.getenv("REVIEW_DB_NAME", "reviews_db")

# Формируем строку подключения
DATABASE_URL = f"postgresql+asyncpg://{REVIEW_DB_USER}:{REVIEW_DB_PASSWORD}@{REVIEW_DB_HOST}:{REVIEW_DB_PORT}/{REVIEW_DB_NAME}"

# Создаем асинхронный движок и фабрику сессий
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def add_is_anonymous_column():
    """Добавляем колонку is_anonymous в таблицу reviews"""
    async with async_session() as session:
        # Проверяем, существует ли уже колонка
        check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name='reviews' AND column_name='is_anonymous'")
        result = await session.execute(check_query)
        exists = result.scalar_one_or_none()
        
        if exists:
            logger.info("Колонка is_anonymous уже существует в таблице reviews")
            return
        
        # Добавляем колонку с значением по умолчанию false
        logger.info("Добавляем колонку is_anonymous в таблицу reviews...")
        alter_query = text("ALTER TABLE reviews ADD COLUMN is_anonymous BOOLEAN NOT NULL DEFAULT false")
        await session.execute(alter_query)
        await session.commit()
        logger.info("Колонка успешно добавлена")

async def main():
    """Основная функция миграции"""
    logger.info("Подключаемся к БД: %s", DATABASE_URL)
    
    try:
        await add_is_anonymous_column()
        logger.info("Миграция успешно выполнена")
    except (SQLAlchemyError, asyncpg.PostgresError):
        logger.exception("Ошибка при выполнении миграции")

if __name__ == "__main__":
    asyncio.run(main()) 