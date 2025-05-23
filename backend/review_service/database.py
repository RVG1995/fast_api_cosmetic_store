"""
Модуль для настройки асинхронного подключения к базе данных и управления сессиями.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from models import Base
from config import settings, get_db_url, logger

# Получаем URL базы данных из настроек
DATABASE_URL = get_db_url()
logger.info(f"URL базы данных: {DATABASE_URL}")

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Для отладки можно установить True, чтобы видеть все SQL-запросы
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    """
    Получение сессии базы данных
    
    Yields:
        AsyncSession: Сессия базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка сессии БД: {str(e)}")
            raise
        finally:
            await session.close()

async def setup_database():
    """
    Инициализация базы данных при запуске приложения
    Создает все необходимые таблицы, если они еще не существуют
    """
    try:
        logger.info("Начало инициализации базы данных...")
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise 