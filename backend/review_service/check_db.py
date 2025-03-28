#!/usr/bin/env python3
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_check")

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

async def check_reviews():
    """Проверяем наличие отзывов в БД"""
    async with async_session() as session:
        # Подсчитываем общее количество отзывов
        count_result = await session.execute(text("SELECT COUNT(*) FROM reviews"))
        count = count_result.scalar_one()
        print(f"Всего отзывов в БД: {count}")
        
        if count > 0:
            # Получаем информацию об отзывах
            reviews_result = await session.execute(
                text("SELECT id, review_type, product_id, is_hidden FROM reviews")
            )
            
            print("\nСписок отзывов:")
            print("=" * 50)
            for row in reviews_result:
                print(f"ID: {row[0]}, Тип: {row[1]}, Товар ID: {row[2]}, Скрыт: {row[3]}")
            print("=" * 50)
            
            # Проверяем отзывы для товара с ID = 19
            product_reviews = await session.execute(
                text("SELECT id, review_type, is_hidden FROM reviews WHERE product_id = 19")
            )
            
            rows = list(product_reviews)
            print(f"\nОтзывы для товара ID=19: {len(rows)}")
            for row in rows:
                print(f"ID: {row[0]}, Тип: {row[1]}, Скрыт: {row[2]}")
            
            # Проверяем отзывы для магазина
            store_reviews = await session.execute(
                text("SELECT id, review_type, is_hidden FROM reviews WHERE review_type = 'store'")
            )
            
            rows = list(store_reviews)
            print(f"\nОтзывы для магазина: {len(rows)}")
            for row in rows:
                print(f"ID: {row[0]}, Тип: {row[1]}, Скрыт: {row[2]}")

async def main():
    """Основная функция для проверки БД"""
    print("Проверка базы данных отзывов...")
    print(f"Подключаемся к: {DATABASE_URL}")
    
    try:
        await check_reviews()
    except Exception as e:
        print(f"Ошибка при проверке БД: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 