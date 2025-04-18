from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import logging
import pathlib
from typing import AsyncGenerator

from models import Base

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_database")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info(f"Загружаем .env из {env_file}")
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    logger.info(f"Загружаем .env из {parent_env_file}")
    load_dotenv(dotenv_path=parent_env_file)
else:
    logger.warning("Файл .env не найден!")

# Получаем URL подключения к базе данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/cart_db")
logger.info(f"URL базы данных: {DATABASE_URL}")

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
        logger.error(f"Ошибка при создании таблиц: {str(e)}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет асинхронную сессию базы данных"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка при работе с базой данных: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close() 