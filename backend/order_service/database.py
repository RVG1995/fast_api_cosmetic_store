"""Модуль для работы с базой данных заказов."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import Base
from config import settings, get_db_url

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_database")

# Получаем URL подключения к базе данных из конфигурации
DATABASE_URL = get_db_url()
logger.info("URL базы данных: %s", DATABASE_URL)

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