import httpx
import logging
import os
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timezone
import jwt
from cache import get_cached_data, set_cached_data, redis_client
from dotenv import load_dotenv
from dependencies import _get_service_token, NOTIFICATION_SERVICE_URL, AUTH_SERVICE_URL

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("order_service.notification_api")

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
                    json={"event_type":event_type, "user_id":user_id, "payload":payload}
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