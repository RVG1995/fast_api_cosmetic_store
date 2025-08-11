"""Утилиты аутентификации и авторизации для сервиса заказов."""

import logging
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
import jwt

from config import settings
from cache import cache_service

async def is_jti_revoked(jti: str) -> bool:
    try:
        revoked = await cache_service.get(f"revoked:jti:{jti}")
        return bool(revoked)
    except Exception:
        return False

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_auth")

# Константы для JWT из настроек
ALGORITHM = "RS256"
ISSUER = getattr(settings, "JWT_ISSUER", "auth_service")
VERIFY_AUDIENCE = getattr(settings, "VERIFY_JWT_AUDIENCE", False)
AUDIENCE = getattr(settings, "JWT_AUDIENCE", None)
AUTH_SERVICE_URL = getattr(settings, "AUTH_SERVICE_URL", "http://localhost:8000")
JWKS_URL = f"{AUTH_SERVICE_URL}/auth/.well-known/jwks.json"
_jwks_client = jwt.PyJWKClient(JWKS_URL)

logger.info("Загружена конфигурация JWT")

# Схема авторизации через OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Класс пользователя для хранения данных из токена
class User:
    """Класс для хранения данных пользователя из JWT токена."""
    def __init__(self, id: int, is_admin: bool = False, is_super_admin: bool = False, is_active: bool = True):
        self.id = id
        self.is_admin = is_admin
        self.is_super_admin = is_super_admin
        self.is_active = is_active

async def get_token_from_cookie_or_header(
    token: Annotated[str, Depends(oauth2_scheme)] = None,
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Пытается получить JWT токен из разных источников:
    1. OAuth2 Bearer Token
    2. Cookie 'access_token'
    3. Header 'Authorization' в формате Bearer
    """
    # Логируем все возможные источники токена
    logger.debug("OAuth token: %s", token)
    logger.debug("Cookie token: %s", access_token)
    logger.debug("Header Authorization: %s", authorization)
    
    # Приоритет токенов: сначала OAuth2, затем Cookie, потом Header
    if token:
        return token
        
    if access_token:
        return access_token
        
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
    
    return None

# Зависимость для получения текущего пользователя
async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """Получает текущего пользователя из JWT токена в cookie или заголовке Authorization.
    
    Args:
        request: FastAPI Request объект
        access_token: JWT токен из cookie
        authorization: JWT токен из заголовка Authorization
        
    Returns:
        User объект или None если токен невалидный или отсутствует
    """
    logger.info("Запрос авторизации: %s %s", request.method, request.url.path)
    
    # Если нет куки-токена, проверяем заголовок Authorization
    if not access_token and authorization:
        if authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
            logger.info("Токен получен из заголовка Authorization")
        else:
            logger.warning("Заголовок Authorization не содержит Bearer токен")
    
    if not access_token:
        logger.warning("Токен не найден ни в cookie, ни в заголовке Authorization")
        return None
    
    try:
        logger.info("Попытка декодирования токена")
        
        # Стандартная проверка подписи/срока + issuer/audience
        signing_key = _jwks_client.get_signing_key_from_jwt(access_token).key
        decode_kwargs = {
            "algorithms": [ALGORITHM],
            "issuer": ISSUER,
            "options": {"verify_aud": VERIFY_AUDIENCE},
        }
        if VERIFY_AUDIENCE and AUDIENCE:
            decode_kwargs["audience"] = AUDIENCE
        payload = jwt.decode(access_token, signing_key, **decode_kwargs)

        # Проверка отзыва jti в Redis
        jti = payload.get("jti")
        if jti and await is_jti_revoked(jti):
            logger.warning("Токен с jti=%s отозван", jti)
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("В токене отсутствует sub с ID пользователя")
            return None
        
        # Если это сервисный токен — игнорируем пользователя
        if payload.get("scope") == "service":
            logger.info("Обнаружен сервисный JWT, пропускаем user-контекст")
            return None

        # Добавляем проверку ролей из токена
        is_admin = payload.get("is_admin", False)
        is_super_admin = payload.get("is_super_admin", False)
        is_active = payload.get("is_active", True)
        
        logger.info("Токен декодирован успешно: user_id=%s, is_admin=%s, is_super_admin=%s", user_id, is_admin, is_super_admin)
        
        return User(
            id=int(user_id),
            is_admin=is_admin,
            is_super_admin=is_super_admin,
            is_active=is_active
        )
    except jwt.InvalidSignatureError:
        logger.error("Ошибка декодирования JWT: Неверная подпись токена")
        return None
    except jwt.ExpiredSignatureError:
        logger.error("Ошибка декодирования JWT: Токен просрочен")
        return None

def check_admin_access(user: Optional[User] = Depends(get_current_user)):
    """Проверяет, что пользователь аутентифицирован и имеет права администратора"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    if not (user.is_admin or user.is_super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуются права администратора"
        )
    return user

def check_super_admin_access(user: Optional[User] = Depends(get_current_user)):
    """Проверяет, что пользователь аутентифицирован и имеет права супер-администратора"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуются права супер-администратора"
        )
    return user

def check_authenticated(user: Optional[User] = Depends(get_current_user)):
    """Проверяет, что пользователь аутентифицирован"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    return user
