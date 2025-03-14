from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Computed, Boolean, Text, select, ForeignKey, CheckConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from models import Base

import os
from typing import List, Optional, AsyncGenerator
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение URL базы данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/product_db")
logger.info(f"URL базы данных: {DATABASE_URL}")

engine = create_async_engine(DATABASE_URL, echo = True)

new_session = async_sessionmaker(engine,expire_on_commit=False)

async def get_session()-> AsyncGenerator[AsyncSession, None]:
    async with new_session() as session:
        yield session



async def setup_database():
    """
    Создает все таблицы в базе данных на основе описанных моделей.
    """
    async with engine.begin() as conn:
        #await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
