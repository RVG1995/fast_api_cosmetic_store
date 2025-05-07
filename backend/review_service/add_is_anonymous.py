#!/usr/bin/env python3
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings, get_db_url, logger

# Формируем строку подключения из конфигурации
DATABASE_URL = get_db_url()

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
    logger.info(f"Подключаемся к БД: {DATABASE_URL}")
    
    try:
        await add_is_anonymous_column()
        logger.info("Миграция успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 