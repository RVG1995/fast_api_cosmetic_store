"""Модуль для работы с JWT токенами."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, Any

import jwt

from config import settings, get_access_token_expires_delta, get_service_token_expires_delta

logger = logging.getLogger(__name__)

# Загружаем настройки JWT из конфигурации
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

class TokenService:
    """Сервис для работы с JWT токенами"""
    
    @staticmethod
    async def create_access_token(data: Dict[str, Any], expires_delta: Optional[datetime] = None) -> Tuple[str, str]:
        """
        Создает JWT токен с улучшенными параметрами безопасности
        
        Args:
            data: Данные для кодирования в токен
            expires_delta: Срок действия токена
            
        Returns:
            Tuple[str, str]: Токен и его уникальный идентификатор (jti)
        """
        to_encode = data.copy()
        
        # Устанавливаем время истечения токена
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + get_access_token_expires_delta()
        
        # Добавляем уникальный идентификатор токена для возможности отзыва
        jti = str(uuid.uuid4())
        
        # Добавляем стандартные JWT-клеймы
        to_encode.update({
            "exp": expire,  # Expiration time
            "iat": datetime.now(timezone.utc),  # Issued at
            "jti": jti,  # JWT ID
            "nbf": datetime.now(timezone.utc)  # Not valid before
        })
        
        # Создаем токен
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info("Создан токен с JTI: %s, истечет: %s", jti, expire)
        
        return encoded_jwt, jti
    
    @staticmethod
    async def decode_token(token: str) -> Dict[str, Any]:
        """
        Декодирует и проверяет JWT токен
        
        Args:
            token: JWT токен для декодирования
            
        Returns:
            Dict[str, Any]: Данные из токена
            
        Raises:
            jwt.PyJWTError: При ошибке декодирования
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Попытка использования истекшего токена")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning("Недействительный токен: %s", str(e))
            raise
    
    @staticmethod
    async def get_token_expiry(token: str) -> Optional[datetime]:
        """
        Получает время истечения токена
        
        Args:
            token: JWT токен
            
        Returns:
            Optional[datetime]: Время истечения токена или None при ошибке
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": True})
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=timezone.utc)
            return None
        except (jwt.InvalidTokenError, jwt.DecodeError) as e:
            logger.error("Ошибка при получении времени истечения токена: %s", str(e))
            return None

    @staticmethod
    async def create_service_token(service_name: str = "auth_service") -> str:
        """
        Создает сервисный JWT токен для межсервисного взаимодействия
        
        Args:
            service_name: Имя сервиса-отправителя
            
        Returns:
            str: JWT токен для межсервисного взаимодействия
        """
        expires_delta = get_service_token_expires_delta()
        expire = datetime.now(timezone.utc) + expires_delta
        
        to_encode = {
            "sub": service_name, 
            "scope": "service",
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt 