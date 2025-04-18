import httpx
import logging
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Cookie, Header
from fastapi.security import OAuth2PasswordBearer

from .config import AUTH_SERVICE_URL, JWT_SECRET_KEY, ALGORITHM, INTERNAL_SERVICE_KEY

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
logger = logging.getLogger("notifications_service.auth")

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
    token: Optional[str] = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
) -> Optional[User]:
    # Берем токен из cookie или из Authorization
    if not token and authorization:
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else authorization
    if not token:
        return None
    try:
        # Декодируем JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except Exception as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    # Запрашиваем профиль у Auth-сервиса
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{AUTH_SERVICE_URL}/auth/users/me/profile", headers=headers, timeout=5.0)
        if resp.status_code != 200:
            logger.warning(f"Auth service returned {resp.status_code}")
            return None
        data = resp.json()
        if "id" not in data:
            data["id"] = int(user_id)
        return User(data)
    except Exception as e:
        logger.error(f"Error calling auth service: {e}")
        return User({"id": int(user_id), "email": "", "first_name": "", "last_name": ""})

async def require_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь аутентифицирован"""
    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
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