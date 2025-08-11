"""Утилиты аутентификации и авторизации для сервиса уведомлений."""

import logging
from typing import Optional, Dict, Any

import httpx
import jwt
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

from config import settings
from cache import cache_service

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
logger = logging.getLogger("notifications_service.auth")

bearer_scheme = HTTPBearer(auto_error=False)
ALGORITHM = "RS256"
AUTH_SERVICE_URL = getattr(settings, "AUTH_SERVICE_URL", "http://localhost:8000")
JWKS_URL = f"{AUTH_SERVICE_URL}/auth/.well-known/jwks.json"
_jwks_client = jwt.PyJWKClient(JWKS_URL)
async def verify_service_jwt(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> bool:
    """Проверяет JWT токен с scope 'service'"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(cred.credentials).key
        payload = jwt.decode(cred.credentials, signing_key, algorithms=[ALGORITHM])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True

class User:
    """Класс представления пользователя"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.email = data.get("email")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.is_active = data.get("is_active", False)
        self.is_admin = data.get("is_admin", False)
        self.is_super_admin = data.get("is_super_admin", False)

async def get_current_user(
    request: Request,
    authorization: str = Depends(oauth2_scheme)
) -> Optional[User]:
    """Получает текущего пользователя из JWT токена и профиля из Auth-сервиса.
    
    Args:
        request: FastAPI Request объект
        authorization: Токен из заголовка Authorization
        
    Returns:
        User объект или None если пользователь не аутентифицирован
    """
    # Получаем токен из кук
    token = None
    if "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    
    # Если нет в куках, смотрим заголовок авторизации
    if not token and authorization:
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else authorization

    
    if not token:
        logger.warning("No token found in cookie or Authorization header")
        return None
    
    try:
        # Декодируем JWT с issuer + опциональной audience
        ISSUER = getattr(settings, "JWT_ISSUER", "auth_service")
        VERIFY_AUDIENCE = getattr(settings, "VERIFY_JWT_AUDIENCE", False)
        AUDIENCE = getattr(settings, "JWT_AUDIENCE", None)
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        decode_kwargs = {
            "algorithms": [ALGORITHM],
            "issuer": ISSUER,
            "options": {"verify_aud": VERIFY_AUDIENCE},
        }
        if VERIFY_AUDIENCE and AUDIENCE:
            decode_kwargs["audience"] = AUDIENCE
        payload = jwt.decode(token, signing_key, **decode_kwargs)

        # Отозван ли jti
        jti = payload.get("jti")
        if jti:
            revoked = await cache_service.get(f"revoked:jti:{jti}")
            if revoked:
                logger.warning("JWT validation failed: revoked jti %s", jti)
                return None

        # Сервисные JWT не дают user-контекст
        if payload.get("scope") == "service":
            return None

        user_id = payload.get("sub")
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError, jwt.DecodeError) as e:
        logger.warning("JWT validation failed: %s", e)
        return None
    
    # Запрашиваем профиль у Auth-сервиса
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client:
            logger.debug("Requesting user profile from %s", settings.AUTH_SERVICE_URL)
            resp = await client.get(f"{settings.AUTH_SERVICE_URL}/auth/users/me/profile", headers=headers, timeout=5.0)
        if resp.status_code != 200:
            logger.warning("Auth service returned %d: %s", resp.status_code, resp.text)
            # При ошибке получаем None, без создания базового профиля
            return None
        
        data = resp.json()
        if "id" not in data:
            data["id"] = int(user_id)
        
        # Обязательно устанавливаем is_active=True если не указано
        if "is_active" not in data:
            data["is_active"] = True
            
        logger.debug("User data from auth service: %s", data)
        return User(data)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error("Error calling auth service: %s", e)
        # При исключении возвращаем None без доверия к токену
        return None

async def require_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь аутентифицирован"""
    if not current_user:
        logger.warning("User not authenticated - current_user is None")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not getattr(current_user, 'is_active', False):
        logger.warning("User %s is not active", current_user.id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")
    return current_user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь имеет админские права"""
    if not current_user or not (current_user.is_admin or current_user.is_super_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь имеет супер-админ права"""
    if not current_user or not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return current_user
