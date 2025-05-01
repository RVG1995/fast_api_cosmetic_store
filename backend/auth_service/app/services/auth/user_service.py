"""Модуль для работы с пользователями и их учетными данными."""

import logging
import secrets
from datetime import datetime
from typing import Optional, Tuple
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import httpx

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
        is_active: bool = False,
        personal_data_agreement: bool = False,
        notification_agreement: bool = False
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
            activation_token=None if is_active else activation_token,
            personal_data_agreement=personal_data_agreement,
            notification_agreement=notification_agreement
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
        except SQLAlchemyError as e:
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
        except SQLAlchemyError as e:
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
        except SQLAlchemyError as e:
            logger.error("Ошибка при отправке письма активации: %s", str(e))
            return False
    
    @staticmethod
    async def activate_notifications(user_id: str, email: str, is_admin: bool = False, service_token: str = None) -> bool:
        """
        Активация всех доступных уведомлений для пользователя
        
        Args:
            user_id: ID пользователя
            email: Email пользователя
            is_admin: Флаг администратора
            service_token: Сервисный JWT токен для авторизации
            
        Returns:
            bool: True при успешной активации, иначе False
        """
        try:            
            # URL сервиса уведомлений
            notifications_service_url = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8005")
            
            # Проверяем, был ли передан сервисный токен
            if not service_token:
                logger.error("Отсутствует сервисный токен для активации уведомлений")
                return False
            
            # Отправляем запрос на активацию уведомлений
            async with httpx.AsyncClient() as client:
                # Подготавливаем данные
                activation_data = {
                    "user_id": user_id,
                    "email": email,
                    "is_admin": is_admin
                }
                
                # Логируем детали запроса для отладки
                logger.info(
                    "Отправка запроса на активацию уведомлений: URL=%s, TOKEN=%s..., DATA=%s", 
                    f"{notifications_service_url}/notifications/service/activate-notifications",
                    service_token[:15] if service_token else "None",
                    activation_data
                )
                
                # Отправляем запрос
                headers = {"Authorization": f"Bearer {service_token}"}
                
                # Увеличиваем таймаут и добавляем отладочную информацию
                try:
                    response = await client.post(
                        f"{notifications_service_url}/notifications/service/activate-notifications",
                        headers=headers,
                        json=activation_data,
                        timeout=15.0  # Увеличиваем таймаут для запроса
                    )
                    
                    # Логируем ответ для отладки
                    logger.info(
                        "Получен ответ от сервиса уведомлений: CODE=%s, BODY=%s", 
                        response.status_code, 
                        response.text
                    )
                    
                    if response.status_code not in (200, 201, 204):
                        logger.error(
                            "Ошибка при активации уведомлений: %s, %s", 
                            response.status_code, 
                            response.text
                        )
                        return False
                    
                    result = response.json()
                    logger.info(
                        "Активировано %s уведомлений для пользователя %s", 
                        result.get("activated_count", 0),
                        user_id
                    )
                except httpx.RequestError as e:
                    logger.error("Ошибка HTTP запроса при активации уведомлений: %s", str(e))
                    return False
            
            return True
            
        except httpx.HTTPError as e:
            logger.error("Ошибка при активации уведомлений: %s", str(e))
            return False

# Создаем глобальный экземпляр сервиса для использования в приложении
user_service = UserService()
