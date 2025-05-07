"""Модуль конфигурации и инициализации базы данных для сервиса аутентификации."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from models import Base, UserModel
from utils import get_password_hash
from config import settings, get_db_url

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение URL базы данных из конфигурации
DATABASE_URL = get_db_url()

engine = create_async_engine(DATABASE_URL, echo = True)

new_session = async_sessionmaker(engine,expire_on_commit=False)

async def get_session()-> AsyncGenerator[AsyncSession, None]:
    """Возвращает асинхронную сессию базы данных."""
    async with new_session() as session:
        yield session

async def create_superadmin() -> None:
    """Создает суперпользователя, если он не существует"""
    try:
        # Получаем данные из конфигурации
        admin_email = settings.SUPERADMIN_EMAIL
        admin_password = settings.SUPERADMIN_PASSWORD
        first_name = settings.SUPERADMIN_FIRST_NAME
        last_name = settings.SUPERADMIN_LAST_NAME
        
        if not admin_email or not admin_password:
            logger.warning("SUPERADMIN_EMAIL или SUPERADMIN_PASSWORD не указаны в .env файле")
            return
        
        # Используем уже существующую сессию new_session
        async with new_session() as session:
            # Проверяем, существует ли уже суперпользователь с заданным email
            existing_admin = await UserModel.get_by_email(session, admin_email)
            
            if existing_admin and existing_admin.is_super_admin:
                logger.info("Суперпользователь с email %s уже существует", admin_email)
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
                is_super_admin=True,
                personal_data_agreement=True,
                notification_agreement=True
            )
            
            session.add(superadmin)
            await session.commit()
            logger.info("Суперпользователь создан с email: %s", admin_email)
    except SQLAlchemyError as e:
        logger.error("Ошибка при создании суперпользователя: %s", e)

async def create_default_user() -> None:
    """Создает обычного пользователя, если он не существует"""
    try:
        # Получаем данные из конфигурации
        user_email = settings.DEFAULT_USER_EMAIL
        user_password = settings.DEFAULT_USER_PASSWORD
        first_name = settings.DEFAULT_USER_FIRST_NAME
        last_name = settings.DEFAULT_USER_LAST_NAME
        
        if not user_email or not user_password:
            logger.warning("DEFAULT_USER_EMAIL или DEFAULT_USER_PASSWORD не указаны в .env файле")
            return
        
        # Используем уже существующую сессию new_session
        async with new_session() as session:
            # Проверяем, существует ли уже пользователь с заданным email
            existing_user = await UserModel.get_by_email(session, user_email)
            
            if existing_user:
                logger.info("Пользователь с email %s уже существует", user_email)
                return
                
            # Создаем обычного пользователя
            hashed_password = await get_password_hash(user_password)
            
            default_user = UserModel(
                email=user_email,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_admin=False,
                is_super_admin=False,
                personal_data_agreement=True,
                notification_agreement=True
            )
            
            session.add(default_user)
            await session.commit()
            logger.info("Пользователь создан с email: %s", user_email)
    except SQLAlchemyError as e:
        logger.error("Ошибка при создании пользователя: %s", e)

async def setup_database():
    """
    Создает все таблицы в базе данных на основе описанных моделей.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
