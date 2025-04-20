import httpx
import logging
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("order_service.notification_api")

NOTIFICATION_SERVICE_URL = "http://localhost:8005"  # Адрес сервиса уведомлений
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")  # Адрес сервиса авторизации
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")  # устаревший, не используется при client_credentials

# Client credentials for service-to-service auth
SERVICE_CLIENTS_RAW = os.getenv("SERVICE_CLIENTS_RAW", "")
SERVICE_CLIENTS = {
    k: v for k,v in []  # removed mapping, not used
}
SERVICE_CLIENT_ID = os.getenv("SERVICE_CLIENT_ID","orders")
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"

SERVICE_CLIENT_SECRET = os.getenv("SERVICE_CLIENT_SECRET")  # set in .env
async def _get_service_token():
    secret = SERVICE_CLIENT_SECRET
    if not secret:
        raise RuntimeError("SERVICE_CLIENT_SECRET not set")
    data = {
        "grant_type":"client_credentials",
        "client_id": SERVICE_CLIENT_ID,
        "client_secret": secret
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
        r.raise_for_status()
        return r.json()["access_token"]

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
        # Используем OAuth2 client_credentials вместо service-key
        token = await _get_service_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        url = f"{NOTIFICATION_SERVICE_URL}/notifications/settings/events"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, timeout=5.0, json={"event_type": event_type, "user_id": str(user_id), "payload": payload})
            
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