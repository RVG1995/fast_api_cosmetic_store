from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config import get_db_url
from models import Base
DATABASE_URL = get_db_url()
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def get_async_session():
    async def _get_session():
        async with async_session_maker() as session:
            yield session
    return _get_session 


async def setup_database():
    """
    Создает все таблицы в базе данных на основе описанных моделей.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)