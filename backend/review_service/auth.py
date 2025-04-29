"""Модуль для аутентификации и авторизации пользователей в review_service."""
import os
import logging
import json
from typing import Dict, Optional, Any
import requests
import jwt
from fastapi import HTTPException, Depends, Cookie, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_service.auth")

# URL сервиса аутентификации
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Секретный ключ для проверки токенов
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
ALGORITHM = "HS256"

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
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Получение текущего пользователя на основе JWT токена
    
    Args:
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
            logger.info("Декодирован токен, payload: %s", payload)
            if not user_id:
                logger.warning("Токен не содержит идентификатор пользователя (sub)")
                return None
        except jwt.PyJWTError as e:
            logger.warning("Ошибка декодирования токена: %s", e)
            return None
        
        # Получаем данные о пользователе через API аутентификации
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Запрашиваем данные пользователя из сервиса auth: %s/auth/users/me/profile", AUTH_SERVICE_URL)
        try:
            response = requests.get(f"{AUTH_SERVICE_URL}/auth/users/me/profile", headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning("Не удалось получить профиль пользователя: код %s", response.status_code)
                logger.warning("Ответ сервера: %s", response.text[:500])
                return None
            
            try:
                user_data = response.json()
                logger.info("Получены данные пользователя: %s", json.dumps(user_data))
                
                # Защита от отсутствия обязательных полей
                if "id" not in user_data:
                    user_data["id"] = int(user_id)
                
                return User(user_data)
            except ValueError as e:
                logger.error("Ошибка при обработке ответа сервиса аутентификации: %s", e)
                return User({"id": int(user_id), "email": "", "first_name": "Пользователь", "last_name": str(user_id)})
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка соединения с сервисом аутентификации: %s", e)
            # Создаем минимальный объект пользователя, чтобы процесс мог продолжаться
            return User({"id": int(user_id), "email": "", "first_name": "Пользователь", "last_name": str(user_id)})
    except (jwt.PyJWTError, requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error("Непредвиденная ошибка при получении пользователя: %s", e)
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
