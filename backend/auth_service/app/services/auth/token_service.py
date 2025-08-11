"""Модуль для работы с JWT токенами."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, Any

import jwt
from config import settings, get_access_token_expires_delta, get_service_token_expires_delta, get_refresh_token_expires_delta
from .keys_service import get_private_key_pem, get_kid

logger = logging.getLogger(__name__)

ALGORITHM = "RS256"
ISSUER = settings.JWT_ISSUER
AUDIENCE = settings.JWT_AUDIENCE

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
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,
            "nbf": datetime.now(timezone.utc),
            "iss": ISSUER,
            "aud": AUDIENCE,
        })
        
        # kid в заголовок для выбора ключа
        headers = {"kid": get_kid()}
        # Создаем токен RS256 приватным ключом
        encoded_jwt = jwt.encode(to_encode, get_private_key_pem(), algorithm=ALGORITHM, headers=headers)
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
            options = {"require": ["exp", "iat", "nbf", "iss"], "verify_aud": settings.VERIFY_JWT_AUDIENCE}
            # В самом auth_service мы знаем приватный ключ, но для decode используем публичный
            from .keys_service import get_public_key_pem
            payload = jwt.decode(
                token,
                get_public_key_pem(),
                algorithms=[ALGORITHM],
                audience=AUDIENCE if settings.VERIFY_JWT_AUDIENCE else None,
                options=options,
                issuer=ISSUER,
            )
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
            from .keys_service import get_public_key_pem
            payload = jwt.decode(token, get_public_key_pem(), algorithms=[ALGORITHM], options={"verify_signature": True})
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
        
        headers = {"kid": get_kid()}
        encoded_jwt = jwt.encode(to_encode, get_private_key_pem(), algorithm=ALGORITHM, headers=headers)
        return encoded_jwt 

    @staticmethod
    async def create_refresh_token(user_id: str, device_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Создает refresh-токен с длинным сроком жизни и собственной jti
        """
        expires_delta = get_refresh_token_expires_delta()
        expire = datetime.now(timezone.utc) + expires_delta
        jti = str(uuid.uuid4())
        to_encode = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "nbf": datetime.now(timezone.utc),
            "jti": jti,
            "iss": ISSUER,
            "aud": AUDIENCE,
        }
        if device_id:
            to_encode["device_id"] = device_id
        headers = {"kid": get_kid()}
        return jwt.encode(to_encode, get_private_key_pem(), algorithm=ALGORITHM, headers=headers), jti