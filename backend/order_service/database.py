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
logger = logging.getLogger("order_database")

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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/orders_db")
logger.info(f"URL базы данных: {DATABASE_URL}")

# Создаем движок SQLAlchemy для асинхронной работы с базой данных
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Вывод SQL-запросов в консоль (для отладки)
    future=True,  # Использование новых возможностей SQLAlchemy 2.0
    pool_size=5,  # Размер пула соединений
    max_overflow=10,  # Максимальное количество дополнительных соединений
    pool_timeout=30,  # Таймаут ожидания соединения из пула
    pool_recycle=1800,  # Время жизни соединения (30 минут)
)

# Создаем асинхронную фабрику сессий
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Не истекать объекты после коммита
    autoflush=False,  # Не делать автоматический flush
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

# Функция-генератор для получения сессии базы данных
async def get_db():
    """
    Асинхронный генератор для получения сессии базы данных.
    Используется как зависимость в FastAPI.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Автоматический коммит при успешном выполнении
        except Exception as e:
            await session.rollback()  # Откат транзакции при ошибке
            raise e
        finally:
            await session.close()  # Закрытие сессии в любом случае

# Функция для инициализации базы данных (если необходимо)
async def init_db():
    """
    Инициализация базы данных.
    Может использоваться для создания таблиц или начальных данных.
    """
    # Здесь можно добавить код для инициализации базы данных
    # Например, создание таблиц или добавление начальных данных
    pass 