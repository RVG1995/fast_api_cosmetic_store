"""Модуль для настройки асинхронного подключения к базе данных и управления сессиями."""

import logging
import os
import pathlib

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from sqlalchemy.orm import sessionmaker

from models import Base

from dotenv import load_dotenv
from collections.abc import AsyncGenerator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info("Загружаем .env из %s", env_file)
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    logger.info("Загружаем .env из %s", parent_env_file)
    load_dotenv(dotenv_path=parent_env_file)
else:
    logger.warning("Файл .env не найден!")


# Получение URL базы данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/product_db")
logger.info("URL базы данных: %s", DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo = True)

new_session = async_sessionmaker(engine,expire_on_commit=False)

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
