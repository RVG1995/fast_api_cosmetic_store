"""Утилиты для авторизации и межсервисного взаимодействия."""

import logging
from datetime import datetime, timezone
import jwt
import httpx

from cache import get_cached_data, set_cached_data
from config import settings, get_service_clients

logger = logging.getLogger("order_service.auth_utils")

# Client credentials для межсервисной авторизации
SERVICE_CLIENTS = get_service_clients()
SERVICE_CLIENT_ID = settings.SERVICE_CLIENT_ID
SERVICE_TOKEN_URL = f"{settings.AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = settings.SERVICE_TOKEN_EXPIRE_MINUTES

async def get_service_token():
    """Получает JWT токен для межсервисного взаимодействия."""
    # try cache
    token = await get_cached_data("service_token")
    if token:
        return token
    # Получаем секрет из SERVICE_CLIENTS
    secret = SERVICE_CLIENTS.get(SERVICE_CLIENT_ID)
    if not secret:
        raise RuntimeError(f"Нет секрета для client_id={SERVICE_CLIENT_ID}")
    data = {"grant_type":"client_credentials","client_id":SERVICE_CLIENT_ID,"client_secret":secret}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{settings.AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
        r.raise_for_status()
        new_token = r.json().get("access_token")
    # cache with TTL from exp claim or default
    ttl = SERVICE_TOKEN_EXPIRE_MINUTES*60 - 30
    try:
        payload = jwt.decode(new_token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp() - 5), 1)
    except (jwt.InvalidTokenError, jwt.DecodeError):
        pass
    await set_cached_data("service_token", new_token, ttl)
    return new_token 