"""Модуль для работы с зависимостями."""

import logging
from datetime import datetime, timezone

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from config import settings, get_service_clients
from cache import cache_get, cache_set

# Настройка логирования
logger = logging.getLogger("order_dependencies")

# Получение настроек JWT из конфигурации
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM

# URL сервисов из конфигурации
PRODUCT_SERVICE_URL = settings.PRODUCT_SERVICE_URL
CART_SERVICE_URL = settings.CART_SERVICE_URL
AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL
NOTIFICATION_SERVICE_URL = settings.NOTIFICATION_SERVICE_URL  # Адрес сервиса уведомлений

# Сервисный API-ключ для внутренней авторизации между микросервисами

# Клиентские учетные данные для межсервисной авторизации
SERVICE_CLIENTS_RAW = settings.SERVICE_CLIENTS_RAW
SERVICE_CLIENTS = get_service_clients()
SERVICE_CLIENT_ID = settings.SERVICE_CLIENT_ID
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = settings.SERVICE_TOKEN_EXPIRE_MINUTES

ALGORITHM = JWT_ALGORITHM

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
        except httpx.HTTPError as e:
            logger.error("_get_service_token: failed fetch token: %s", e)
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
    except (jwt.DecodeError, jwt.InvalidTokenError):
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
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True