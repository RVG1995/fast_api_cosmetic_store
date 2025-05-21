"""Утилиты для авторизации и межсервисного взаимодействия."""

import logging
from datetime import datetime, timezone
import jwt
import httpx
from cryptography.fernet import Fernet

from cache import cache_get, cache_set
from config import settings, get_service_clients

logger = logging.getLogger("order_service.auth_utils")

# Client credentials для межсервисной авторизации
SERVICE_CLIENTS = get_service_clients()
SERVICE_CLIENT_ID = settings.SERVICE_CLIENT_ID
SERVICE_TOKEN_URL = f"{settings.AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = settings.SERVICE_TOKEN_EXPIRE_MINUTES

# Добавим в начало файла или в конфиг
# В production ключ должен храниться в защищенном месте (переменных окружения, Vault, KMS)
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

async def get_service_token():
    """Получает JWT токен для межсервисного взаимодействия."""
    # try cache
    encrypted_token = await cache_get("service_token")
    if encrypted_token:
        try:
            # Расшифровываем токен из кэша
            token = cipher_suite.decrypt(encrypted_token).decode('utf-8')
            return token
        except Exception:
            # Если не удалось расшифровать - логируем и получаем новый
            logger.warning("Не удалось расшифровать токен из кэша")
    
    # Получаем секрет из SERVICE_CLIENTS
    secret = SERVICE_CLIENTS.get(SERVICE_CLIENT_ID)
    if not secret:
        raise RuntimeError(f"Нет секрета для client_id={SERVICE_CLIENT_ID}")
    data = {"grant_type":"client_credentials","client_id":SERVICE_CLIENT_ID,"client_secret":secret}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{settings.AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
        r.raise_for_status()
        new_token = r.json().get("access_token")
    
    # Определяем TTL
    ttl = SERVICE_TOKEN_EXPIRE_MINUTES*60 - 30
    try:
        payload = jwt.decode(new_token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp() - 5), 1)
    except (jwt.InvalidTokenError, jwt.DecodeError):
        pass
    
    # Шифруем токен перед сохранением в кэш
    encrypted_token = cipher_suite.encrypt(new_token.encode('utf-8'))
    await cache_set("service_token", encrypted_token, ttl)
    
    return new_token 