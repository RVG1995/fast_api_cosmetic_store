from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from models import Base,UserModel
from typing import AsyncGenerator
import os
from utils import get_password_hash


from dotenv import load_dotenv

load_dotenv()


engine = create_async_engine("postgresql+asyncpg://your_username:your_password@localhost:5433/your_dbname", echo = True)

new_session = async_sessionmaker(engine,expire_on_commit=False)

async def get_session()-> AsyncGenerator[AsyncSession, None]:
    async with new_session() as session:
        yield session

async def create_superadmin() -> None:
    """Создает суперпользователя, если он не существует"""
    try:
        # Получаем данные из .env
        admin_email = os.getenv("SUPERADMIN_EMAIL")
        admin_password = os.getenv("SUPERADMIN_PASSWORD")
        first_name = os.getenv("SUPERADMIN_FIRST_NAME", "Admin")
        last_name = os.getenv("SUPERADMIN_LAST_NAME", "User")
        
        if not admin_email or not admin_password:
            print("SUPERADMIN_EMAIL или SUPERADMIN_PASSWORD не указаны в .env файле")
            return
        
        # Используем уже существующую сессию new_session
        async with new_session() as session:
            # Проверяем, существует ли уже суперпользователь с заданным email
            existing_admin = await UserModel.get_by_email(session, admin_email)
            
            if existing_admin and existing_admin.is_super_admin:
                print(f"Суперпользователь с email {admin_email} уже существует")
                return
                
            # Создаем суперпользователя
            hashed_password = await get_password_hash(admin_password)
            
            superadmin = UserModel(
                email=admin_email,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_admin=True,
                is_super_admin=True
            )
            
            session.add(superadmin)
            await session.commit()
            print(f"Суперпользователь создан с email: {admin_email}")
    except Exception as e:
        print(f"Ошибка при создании суперпользователя: {e}")


async def setup_database():
    """
    Создает все таблицы в базе данных на основе описанных моделей.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
