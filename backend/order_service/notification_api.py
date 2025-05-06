"""
API для работы с уведомлениями в сервисе заказов.
"""
import logging
from typing import Optional, Dict, Any, List
import asyncio

import httpx
from cache import cache_service
from dotenv import load_dotenv
from dependencies import _get_service_token, NOTIFICATION_SERVICE_URL, AUTH_SERVICE_URL

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("order_service.notification_api")

async def check_notification_settings(user_id: int, event_type: str, email: str, order_id: int) -> Dict[str, bool]:
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
                    json={"event_type":event_type, "user_id":user_id, "email":email, "order_id":order_id}
                )
                if response.status_code == 401:
                    # token expired - clear cache and retry
                    await cache_service.delete("service_token")
                    await asyncio.sleep(delay)
                    continue
                break
        
        # now response contains result
        if response.status_code == 200:
            logger.info("Получены настройки уведомлений для пользователя %s", user_id)
            return {"ok": True}  # По умолчанию уведомления включены
        elif response.status_code == 404:
            # Настройки не найдены, используем значения по умолчанию
            logger.info("Настройки уведомлений для пользователя %s, тип события %s не найдены", user_id, event_type)
            return {"404": False}
        else:
            logger.warning("Ошибка при получении настроек уведомлений: %s, %s", response.status_code, response.text)
            return {"warning": False}
                
    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error("Ошибка при запросе настроек уведомлений: %s", str(e))

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
                logger.info("Получен список администраторов: %s пользователей", len(admins))
                return admins
            else:
                logger.warning("Ошибка при получении списка администраторов: %s, %s", response.status_code, response.text)
                return []
                
    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error("Ошибка при запросе списка администраторов: %s", str(e))
        return []
