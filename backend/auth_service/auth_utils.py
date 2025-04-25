from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy import select
from typing import Optional, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from models import UserModel
import jwt
import os
import logging
from fastapi.security import OAuth2PasswordBearer
from app.services import (
    TokenService,
    user_service,
    session_service
)

# Настройка логгера
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
ALGORITHM = "HS256"

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
    logger.debug(f"Получен токен из куки: {token and 'Yes' or 'No'}")
    logger.debug(f"Получен токен из заголовка: {authorization and 'Yes' or 'No'}")

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
            logger.warning(f"Попытка использования отозванного токена с JTI: {jti}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен был отозван",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка декодирования токена: {str(e)}")
        raise credentials_exception
    
    # Получаем пользователя с использованием кэширования
    user = await user_service.get_user_by_id(session, int(user_id))
    if user is None:
        logger.error(f"Пользователь с ID {user_id} не найден")
        raise credentials_exception
        
    # Проверяем, активен ли пользователь
    if not user.is_active:
        logger.warning(f"Попытка авторизации с неактивным аккаунтом, ID: {user_id}")
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