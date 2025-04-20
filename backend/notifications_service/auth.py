import httpx
import logging
import jwt
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status, Cookie, Header, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

from .config import AUTH_SERVICE_URL, JWT_SECRET_KEY, ALGORITHM, INTERNAL_SERVICE_KEY

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
logger = logging.getLogger("notifications_service.auth")

bearer_scheme = HTTPBearer(auto_error=False)
async def verify_service_jwt(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> bool:
    """Проверяет JWT токен с scope 'service'"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
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

async def verify_service_key(service_key: str = Header(None, alias="service-key")) -> bool:
    """Проверяет секретный ключ межсервисного взаимодействия"""
    if not service_key or service_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service key")
    return True

async def get_current_user(
    request: Request,
    authorization: str = Depends(oauth2_scheme)
) -> Optional[User]:
    # Получаем токен из кук
    token = None
    if "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    
    # Если нет в куках, смотрим заголовок авторизации
    if not token and authorization:
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else authorization
    
    # Логируем для отладки
    logger.debug(f"Cookie token: {token[:10] + '...' if token else None}")
    logger.debug(f"Authorization header: {authorization[:10] + '...' if authorization else None}")
    
    if not token:
        logger.warning("No token found in cookie or Authorization header")
        return None
    
    try:
        # Декодируем JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        logger.debug(f"Decoded JWT, user_id: {user_id}")
    except Exception as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    
    # Запрашиваем профиль у Auth-сервиса
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Requesting user profile from {AUTH_SERVICE_URL}")
            resp = await client.get(f"{AUTH_SERVICE_URL}/auth/users/me/profile", headers=headers, timeout=5.0)
        if resp.status_code != 200:
            logger.warning(f"Auth service returned {resp.status_code}: {resp.text}")
            # При ошибке получаем None, без создания базового профиля
            return None
        
        data = resp.json()
        if "id" not in data:
            data["id"] = int(user_id)
        
        # Обязательно устанавливаем is_active=True если не указано
        if "is_active" not in data:
            data["is_active"] = True
            
        logger.debug(f"User data from auth service: {data}")
        return User(data)
    except Exception as e:
        logger.error(f"Error calling auth service: {e}")
        # При исключении возвращаем None без доверия к токену
        return None

async def require_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь аутентифицирован"""
    if not current_user:
        logger.warning("User not authenticated - current_user is None")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not getattr(current_user, 'is_active', False):
        logger.warning(f"User {current_user.id} is not active")
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