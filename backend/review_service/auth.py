import httpx
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union
from fastapi import HTTPException, Depends, Cookie, Request, status
from fastapi.security import OAuth2PasswordBearer
import json

from config import settings, logger

# URL сервиса аутентификации
AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Секретный ключ для проверки токенов
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

class User:
    """Класс представления пользователя в системе"""
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get("id")
        self.email = user_data.get("email")
        self.first_name = user_data.get("first_name")
        self.last_name = user_data.get("last_name")
        self.is_active = user_data.get("is_active", False)
        self.is_admin = user_data.get("is_admin", False)
        self.is_super_admin = user_data.get("is_super_admin", False)

    @property
    def is_authenticated(self) -> bool:
        """Проверка, аутентифицирован ли пользователь"""
        return self.is_active

    @property
    def full_name(self) -> str:
        """Получение полного имени пользователя"""
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"User(id={self.id}, email={self.email}, is_admin={self.is_admin})"

async def get_current_user(
    request: Request,
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Получение текущего пользователя на основе JWT токена
    
    Args:
        request: Запрос
        token: Токен из куки
        authorization: Токен из заголовка Authorization
        
    Returns:
        User: Объект пользователя или None
    """
    try:
        # Получаем токен из кук или заголовка Authorization
        if not token and authorization:
            if authorization.startswith("Bearer "):
                token = authorization[7:]
            else:
                token = authorization
        
        if not token:
            logger.debug("Токен не найден, пользователь не аутентифицирован")
            return None
        
        try:
            # Декодируем токен локально
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            logger.info(f"Декодирован токен, payload: {payload}")
            if not user_id:
                logger.warning("Токен не содержит идентификатор пользователя (sub)")
                return None
        except jwt.PyJWTError as e:
            logger.warning(f"Ошибка декодирования токена: {str(e)}")
            return None
        
        # Получаем данные о пользователе через API аутентификации
        headers = {"Authorization": f"Bearer {token}"}
        logger.info(f"Запрашиваем данные пользователя из сервиса auth: {AUTH_SERVICE_URL}/auth/users/me/profile")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{AUTH_SERVICE_URL}/auth/users/me/profile", headers=headers, timeout=10.0)
            
            if response.status_code != 200:
                logger.warning(f"Не удалось получить профиль пользователя: код {response.status_code}")
                logger.warning(f"Ответ сервера: {response.text[:500]}")
                return None
            
            try:
                user_data = response.json()
                logger.info(f"Получены данные пользователя: {json.dumps(user_data)}")
                
                # Защита от отсутствия обязательных полей
                if "id" not in user_data:
                    user_data["id"] = int(user_id)
                
                return User(user_data)
            except Exception as e:
                logger.error(f"Ошибка при обработке ответа сервиса аутентификации: {str(e)}")
                return User({"id": int(user_id), "email": "", "first_name": "Пользователь", "last_name": str(user_id)})
        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения с сервисом аутентификации: {str(e)}")
            # Создаем минимальный объект пользователя, чтобы процесс мог продолжаться
            return User({"id": int(user_id), "email": "", "first_name": "Пользователь", "last_name": str(user_id)})
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении пользователя: {str(e)}")
        return None

async def require_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """
    Проверка аутентификации пользователя. Поднимает исключение, если пользователь не аутентифицирован.
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        User: Аутентифицированный пользователь
        
    Raises:
        HTTPException: Если пользователь не аутентифицирован
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Для выполнения данного действия необходима аутентификация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def require_admin(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """
    Проверка прав администратора. Поднимает исключение, если пользователь не является администратором.
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        User: Пользователь с правами администратора
        
    Raises:
        HTTPException: Если пользователь не аутентифицирован или не является администратором
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Для выполнения данного действия необходима аутентификация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not (current_user.is_admin or current_user.is_super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Для выполнения данного действия необходимы права администратора"
        )
    
    return current_user 