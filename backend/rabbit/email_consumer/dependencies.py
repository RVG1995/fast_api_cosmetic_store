"""Зависимости и утилиты для сервиса RabbitMQ Email Consumer."""

import logging
from datetime import datetime, timezone

from fastapi.security import HTTPBearer
import jwt
import httpx

from config import settings, get_service_clients, logger
from cache import get_cached_data, set_cached_data

# Получение настроек из конфигурации
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM

# URL сервисов
PRODUCT_SERVICE_URL = settings.PRODUCT_SERVICE_URL
CART_SERVICE_URL = settings.CART_SERVICE_URL
ORDER_SERVICE_URL = settings.ORDER_SERVICE_URL
AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL

# Настройки сервисного токена
SERVICE_CLIENT_ID = settings.SERVICE_CLIENT_ID
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = settings.SERVICE_TOKEN_EXPIRE_MINUTES

# Получаем словарь с учетными данными сервисов
SERVICE_CLIENTS = get_service_clients()

bearer_scheme = HTTPBearer(auto_error=False)

async def _get_service_token():
    """Получает токен для межсервисной аутентификации."""
    # Пытаемся получить токен из кэша
    token = await get_cached_data("rabbit_service_token")
    if token:
        return token
        
    # Получаем секрет из настроек
    secret = SERVICE_CLIENTS.get(SERVICE_CLIENT_ID)
    if not secret:
        raise RuntimeError(f"Нет секрета для client_id={SERVICE_CLIENT_ID}")
        
    # Запрашиваем новый токен
    data = {
        "grant_type": "client_credentials",
        "client_id": SERVICE_CLIENT_ID,
        "client_secret": secret
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
        r.raise_for_status()
        new_token = r.json().get("access_token")
        
    # Кэшируем токен с TTL, вычисленным из срока действия токена
    ttl = SERVICE_TOKEN_EXPIRE_MINUTES * 60 - 30
    try:
        payload = jwt.decode(new_token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp() - 5), 1)
    except (jwt.InvalidTokenError, jwt.DecodeError):
        pass
        
    await set_cached_data("rabbit_service_token", new_token, ttl)
    return new_token