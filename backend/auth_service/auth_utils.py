"""Модуль для аутентификации и авторизации пользователей."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from models import UserModel
from config import settings
from app.services import (
    TokenService,
    user_service,
    session_service
)

# Настройка логгера
logger = logging.getLogger(__name__)

# Загружаем настройки из конфигурации
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

SessionDep = Annotated[AsyncSession, Depends(get_session)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

async def get_current_user(
    session: SessionDep, 
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
) -> UserModel:
    """
    Получение текущего пользователя на основе JWT токена
    
    Args:
        session: Сессия базы данных
        token: Токен из cookies
        authorization: Токен из заголовка Authorization
        
    Returns:
        UserModel: Объект пользователя
        
    Raises:
        HTTPException: При ошибке аутентификации
    """
    logger.debug("Получен токен из куки: %s", token and 'Yes' or 'No')
    logger.debug("Получен токен из заголовка: %s", authorization and 'Yes' or 'No')

    actual_token = None
    
    # Если токен есть в куках, используем его
    if token:
        actual_token = token
    # Если в куках нет, но есть в заголовке, используем его
    elif authorization:
        if authorization.startswith('Bearer '):
            actual_token = authorization[7:]
        else:
            actual_token = authorization
    
    if actual_token is None:
        logger.error("Токен не найден ни в куках, ни в заголовке")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден в cookies или заголовке Authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Используем сервис для декодирования токена
        payload = await TokenService.decode_token(actual_token)
        user_id = payload.get("sub")
        
        if user_id is None:
            logger.error("В токене отсутствует поле sub")
            raise credentials_exception
            
        # Проверяем, не отозван ли токен
        jti = payload.get("jti")
        if jti and not await session_service.is_session_active(session, jti):
            logger.warning("Попытка использования отозванного токена с JTI: %s", jti)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен был отозван",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка декодирования токена: %s", str(e))
        raise credentials_exception from e
    
    # Получаем пользователя с использованием кэширования
    user = await user_service.get_user_by_id(session, int(user_id))
    if user is None:
        logger.error("Пользователь с ID %s не найден", user_id)
        raise credentials_exception
        
    # Проверяем, активен ли пользователь
    if not user.is_active:
        logger.warning("Попытка авторизации с неактивным аккаунтом, ID: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Аккаунт не активирован",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user

async def get_admin_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Проверяет, что текущий пользователь - администратор"""
    if not (current_user.is_admin or current_user.is_super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа",
        )
    return current_user

async def get_super_admin_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Проверяет, что текущий пользователь - суперадминистратор"""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа",
        )
    return current_user
