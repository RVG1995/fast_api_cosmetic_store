import httpx
import logging
import os
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timezone
import jwt
from cache import get_cached_data, set_cached_data, redis_client
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("order_service.notification_api")

NOTIFICATION_SERVICE_URL = "http://localhost:8005"  # Адрес сервиса уведомлений
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")  # Адрес сервиса авторизации
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")  # устаревший, не используется при client_credentials

# Client credentials for service-to-service auth
SERVICE_CLIENTS_RAW = os.getenv("SERVICE_CLIENTS_RAW", "")
SERVICE_CLIENTS = {kv.split(":")[0]: kv.split(":")[1] for kv in SERVICE_CLIENTS_RAW.split(",") if ":" in kv}
logger.info(f'Ключи сервисов {SERVICE_CLIENTS.keys()}')
SERVICE_CLIENT_ID = os.getenv("SERVICE_CLIENT_ID","orders")
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = int(os.getenv("SERVICE_TOKEN_EXPIRE_MINUTES", "30"))

async def _get_service_token():
    # try cache
    token = await get_cached_data("service_token")
    if token:
        return token
    # Получаем секрет из общего SERVICE_CLIENTS_RAW
    secret = SERVICE_CLIENTS.get(SERVICE_CLIENT_ID)
    if not secret:
        raise RuntimeError(f"Нет секрета для client_id={SERVICE_CLIENT_ID}")
    data = {"grant_type":"client_credentials","client_id":SERVICE_CLIENT_ID,"client_secret":secret}
    logger.info(f"Requesting service token with data: {data}")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
        r.raise_for_status()
        new_token = r.json().get("access_token")
    # cache with TTL from exp claim or default
    ttl = SERVICE_TOKEN_EXPIRE_MINUTES*60 - 30
    try:
        payload = jwt.decode(new_token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp() - 5), 1)
    except Exception:
        pass
    await set_cached_data("service_token", new_token, ttl)
    return new_token

async def check_notification_settings(user_id: str, event_type: str, payload: dict) -> Dict[str, bool]:
    """
    Проверяет настройки уведомлений пользователя для указанного типа события
    
    Args:
        user_id: ID пользователя
        event_type: Тип события (например, "order.created", "order.status_changed")
        token: JWT токен для авторизации в сервисе уведомлений
        
    Returns:
        Словарь с флагами настроек {email_enabled: bool, push_enabled: bool}
        Если произошла ошибка - возвращает {email_enabled: False, push_enabled: False}
    """
    try:
        # perform with retry on 401
        backoffs = [0.5, 1, 2]
        async with httpx.AsyncClient() as client:
            for delay in backoffs:
                token = await _get_service_token()
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/notifications/settings/events",
                    headers=headers, timeout=5.0,
                    json={"event_type":event_type, "user_id":str(user_id), "payload":payload}
                )
                if response.status_code == 401:
                    # token expired - clear cache and retry
                    await redis_client.delete("service_token")
                    await asyncio.sleep(delay)
                    continue
                break
        
        # now response contains result
        if response.status_code == 200:
            settings = response.json()
            logger.info(f"Получены настройки уведомлений для пользователя {user_id}, тип события {event_type}: {settings}")
            return settings
        elif response.status_code == 404:
            # Настройки не найдены, используем значения по умолчанию
            logger.info(f"Настройки уведомлений для пользователя {user_id}, тип события {event_type} не найдены")
            return {"email_enabled": True, "push_enabled": True}
        else:
            logger.warning(f"Ошибка при получении настроек уведомлений: {response.status_code}, {response.text}")
            return {"email_enabled": True, "push_enabled": True}  # По умолчанию уведомления включены
                
    except Exception as e:
        logger.error(f"Ошибка при запросе настроек уведомлений: {str(e)}")

async def get_admin_users(token: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получает список всех пользователей с правами администратора
    
    Args:
        token: JWT токен для авторизации в сервисе аутентификации
        
    Returns:
        Список пользователей-администраторов
    """
    try:
        # get token with cache
        token = await _get_service_token()
        headers = {"Authorization": f"Bearer {token}"}

        url = f"{AUTH_SERVICE_URL}/auth/admins"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=5.0)
            
            if response.status_code == 200:
                admins = response.json()
                logger.info(f"Получен список администраторов: {len(admins)} пользователей")
                return admins
            else:
                logger.warning(f"Ошибка при получении списка администраторов: {response.status_code}, {response.text}")
                return []
                
    except Exception as e:
        logger.error(f"Ошибка при запросе списка администраторов: {str(e)}")
        return [] 