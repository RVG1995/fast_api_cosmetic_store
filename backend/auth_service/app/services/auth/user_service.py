"""Сервис для работы с пользователями, включая создание, активацию, проверку учетных данных и обновление пароля."""

import logging
import secrets
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserModel
from utils import get_password_hash, verify_password
from .cache_service import cache_service, cached, USER_CACHE_TTL
from ..email_service import send_email_activation_message

logger = logging.getLogger(__name__)

class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    @cached(ttl=USER_CACHE_TTL)
    async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[UserModel]:
        """
        Получение пользователя по ID с использованием кэша
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            Optional[UserModel]: Объект пользователя или None
        """
        logger.debug("Запрос пользователя с ID: %s", user_id)
        user = await UserModel.get_by_id(session, user_id)
        return user
    
    @staticmethod
    @cached(ttl=USER_CACHE_TTL)
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[UserModel]:
        """
        Получение пользователя по email с использованием кэша
        
        Args:
            session: Сессия базы данных
            email: Email пользователя
            
        Returns:
            Optional[UserModel]: Объект пользователя или None
        """
        logger.debug("Запрос пользователя с email: %s", email)
        user = await UserModel.get_by_email(session, email)
        return user
    
    @staticmethod
    async def create_user(
        session: AsyncSession, 
        first_name: str, 
        last_name: str, 
        email: str,
        password: str,
        is_active: bool = False
    ) -> Tuple[UserModel, str]:
        """
        Создание нового пользователя
        
        Args:
            session: Сессия базы данных
            first_name: Имя
            last_name: Фамилия
            email: Email
            password: Пароль (нехешированный)
            is_active: Статус активации
            
        Returns:
            Tuple[UserModel, str]: Созданный пользователь и токен активации
        """
        # Хешируем пароль
        hashed_password = await get_password_hash(password)
        
        # Генерируем токен активации
        activation_token = secrets.token_urlsafe(32)
        
        # Создаем нового пользователя
        new_user = UserModel(
            first_name=first_name,
            last_name=last_name,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
            activation_token=None if is_active else activation_token
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        # Инвалидируем кэш для запросов по email, если он был
        cache_key = f"get_user_by_email:{email}"
        await cache_service.delete(cache_key)
        
        return new_user, activation_token
    
    @staticmethod
    async def activate_user(session: AsyncSession, token: str) -> Optional[UserModel]:
        """
        Активация пользователя по токену
        
        Args:
            session: Сессия базы данных
            token: Токен активации
            
        Returns:
            Optional[UserModel]: Активированный пользователь или None
        """
        user = await UserModel.get_by_activation_token(session, token)
        
        if not user:
            logger.warning("Попытка активации с недействительным токеном: %s", token)
            return None
        
        # Активируем пользователя
        await user.activate(session)
        
        # Инвалидируем кэш
        user_cache_key = f"get_user_by_id:{user.id}"
        email_cache_key = f"get_user_by_email:{user.email}"
        await cache_service.delete(user_cache_key)
        await cache_service.delete(email_cache_key)
        
        return user
    
    @staticmethod
    async def verify_credentials(session: AsyncSession, email: str, password: str) -> Optional[UserModel]:
        """
        Проверка учетных данных пользователя
        
        Args:
            session: Сессия базы данных
            email: Email
            password: Пароль (нехешированный)
            
        Returns:
            Optional[UserModel]: Пользователь при успешной авторизации или None
        """
        user = await UserService.get_user_by_email(session, email)
        
        if not user:
            logger.warning("Попытка входа с несуществующим email: %s", email)
            return None
        
        # Проверяем пароль
        if not await verify_password(password, user.hashed_password):
            logger.warning("Неверный пароль для пользователя: %s", email)
            return None
        
        # Проверяем статус активации
        if not user.is_active:
            logger.warning("Попытка входа в неактивный аккаунт: %s", email)
            return None
        
        return user
    
    @staticmethod
    async def update_last_login(session: AsyncSession, user_id: int) -> bool:
        """
        Обновление времени последнего входа
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            bool: True при успешном обновлении, иначе False
        """
        try:
            user = await UserService.get_user_by_id(session, user_id)
            if user:
                user.last_login = datetime.now()
                await session.commit()
                
                # Инвалидируем кэш
                user_cache_key = f"get_user_by_id:{user_id}"
                email_cache_key = f"get_user_by_email:{user.email}"
                await cache_service.delete(user_cache_key)
                await cache_service.delete(email_cache_key)
                
                return True
            return False
        except (ValueError, AttributeError) as e:
            logger.error("Ошибка при обновлении времени последнего входа: %s", str(e))
            return False
    
    @staticmethod
    async def change_password(session: AsyncSession, user_id: int, new_password: str) -> bool:
        """
        Изменение пароля пользователя
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            new_password: Новый пароль (нехешированный)
            
        Returns:
            bool: True при успешном изменении, иначе False
        """
        try:
            user = await UserService.get_user_by_id(session, user_id)
            if not user:
                return False
            
            # Хешируем новый пароль
            hashed_password = await get_password_hash(new_password)
            user.hashed_password = hashed_password
            
            await session.commit()
            
            # Инвалидируем кэш
            user_cache_key = f"get_user_by_id:{user_id}"
            email_cache_key = f"get_user_by_email:{user.email}"
            await cache_service.delete(user_cache_key)
            await cache_service.delete(email_cache_key)
            
            return True
        except (ValueError, AttributeError) as e:
            logger.error("Ошибка при изменении пароля: %s", str(e))
            return False
    
    @staticmethod
    async def send_activation_email(user_id: str, email: str, activation_token: str) -> bool:
        """
        Отправка письма с активацией аккаунта
        
        Args:
            user_id: ID пользователя
            email: Email пользователя
            activation_token: Токен активации
            
        Returns:
            bool: True при успешной отправке, иначе False
        """
        try:
            # Формируем ссылку активации
            activation_link = f"http://localhost:3000/activate/{activation_token}"
            
            # Отправляем сообщение в очередь
            await send_email_activation_message(user_id, email, activation_link)
            
            return True
        except (ValueError, ConnectionError) as e:
            logger.error("Ошибка при отправке письма активации: %s", str(e))
            return False
            
# Создаем глобальный экземпляр сервиса для использования в приложении
user_service = UserService()
