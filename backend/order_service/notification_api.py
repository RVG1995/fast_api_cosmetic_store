"""
API для работы с уведомлениями в сервисе заказов.
"""
import logging
from typing import Optional, Dict, Any, List
import asyncio

import httpx
from cache import cache_service
from config import settings
from auth_utils import get_service_token

logger = logging.getLogger("order_service.notification_api")

# URL сервисов из конфигурации
NOTIFICATION_SERVICE_URL = settings.NOTIFICATION_SERVICE_URL
AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL

async def check_notification_settings(user_id: int, event_type: str, order_id: int) -> Dict[str, bool]:
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
                token = await get_service_token()
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/notifications/settings/events",
                    headers=headers, timeout=5.0,
                    json={"event_type":event_type, "user_id":user_id, "order_id":order_id}
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
        token = await get_service_token()
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

async def send_low_stock_notification(low_stock_products: List[Dict[str, Any]]) -> bool:
    """
    Отправляет уведомление о низком остатке товаров в сервис уведомлений
    
    Args:
        low_stock_products: Список товаров с низким остатком
            [{"id": int, "name": str, "stock": int}, ...]
        
    Returns:
        bool: True если отправка успешна, False в противном случае
    """
    try:
        logger.info("Отправка уведомления о низком остатке товаров: %d товаров", len(low_stock_products))
        
        # Получаем сервисный токен
        token = await get_service_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Отправляем запрос в сервис уведомлений
        async with httpx.AsyncClient() as client:
            # Используем эндпоинт для отправки уведомлений админам
            # Не указываем user_id, чтобы отправить всем админам
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications/settings/events",
                headers=headers,
                json={
                    "event_type": "product.low_stock",
                    "user_id": None,  # Отправляем всем админам
                    "low_stock_products": low_stock_products
                },
                timeout=5.0
            )
            
            if response.status_code == 200:
                logger.info("Уведомление о низком остатке товаров успешно отправлено")
                return True
            else:
                logger.warning("Ошибка при отправке уведомления: %s, %s", response.status_code, response.text)
                return False
                
    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error("Ошибка при отправке уведомления: %s", str(e))
        return False
