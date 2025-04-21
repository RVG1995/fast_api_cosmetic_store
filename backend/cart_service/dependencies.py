from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header,Cookie
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import os
import jwt
from jwt.exceptions import PyJWTError
import logging
import httpx
from dotenv import load_dotenv
from cache import cache_get, cache_set
from datetime import datetime, timezone

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger("order_dependencies")

# Получение настроек JWT из переменных окружения
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# URL сервисов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8002")

# Сервисный API-ключ для внутренней авторизации между микросервисами
INTERNAL_SERVICE_KEY = os.getenv("SERVICE_API_KEY", "test")

NOTIFICATION_SERVICE_URL = "http://localhost:8005"  # Адрес сервиса уведомлений
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")  # Адрес сервиса авторизации
# Client credentials for service-to-service auth
SERVICE_CLIENTS_RAW = os.getenv("SERVICE_CLIENTS_RAW", "")
SERVICE_CLIENTS = {kv.split(":")[0]: kv.split(":")[1] for kv in SERVICE_CLIENTS_RAW.split(",") if ":" in kv}
SERVICE_CLIENT_ID = os.getenv("SERVICE_CLIENT_ID","carts")
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = int(os.getenv("SERVICE_TOKEN_EXPIRE_MINUTES", "30"))

ALGORITHM = os.getenv("ALGORITHM", "HS256")

bearer_scheme = HTTPBearer(auto_error=False)

async def _get_service_token():
    # try cache
    token = await cache_get("service_token_carts")
    if token:
        return token
    # Debug: покажем текущий client_id и доступные сервисы
    #     # Получаем секрет из SERVICE_CLIENTS
    secret = SERVICE_CLIENTS.get(SERVICE_CLIENT_ID)
    if not secret:
        raise RuntimeError(f"Нет секрета для client_id={SERVICE_CLIENT_ID}")
    # Mask secret for logs (first/last 3 chars)
    data = {"grant_type":"client_credentials","client_id":SERVICE_CLIENT_ID,"client_secret":secret}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"_get_service_token: failed fetch token: {e}")
            raise
        new_token = r.json().get("access_token")
        if not new_token:
            logger.error("_get_service_token: access_token missing in response body")
    # cache with TTL from exp claim or default
    ttl = SERVICE_TOKEN_EXPIRE_MINUTES*60 - 30
    try:
        payload = jwt.decode(new_token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp() - 5), 1)
    except Exception:
        pass
    await cache_set("service_token_carts", new_token, ttl)
    return new_token

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