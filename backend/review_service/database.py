import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import logging
from models import Base

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_service.database")

# Получаем информацию о хосте и порте из переменных окружения
DB_HOST = os.getenv("REVIEW_DB_HOST", "localhost")
DB_PORT = os.getenv("REVIEW_DB_PORT", "5436")
DB_NAME = os.getenv("REVIEW_DB_NAME", "reviews_db")
DB_USER = os.getenv("REVIEW_DB_USER", "postgres")
DB_PASSWORD = os.getenv("REVIEW_DB_PASSWORD", "postgres")

# Формируем URL для подключения к базе данных PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # Для отладки можно установить True, чтобы видеть все SQL-запросы
    future=True,
    poolclass=NullPool  # Отключаем пулинг соединений для асинхронной работы
)

# Создаем фабрику сессий
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

async def get_session() -> AsyncSession:
    """
    Получение сессии базы данных
    
    Yields:
        AsyncSession: Сессия базы данных
    """
    async with SessionLocal() as session:
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