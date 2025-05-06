"""
API для работы с уведомлениями в сервисе заказов.
"""
import logging
from typing import Dict
import asyncio

import httpx
from cache import cache_service
from dotenv import load_dotenv
from dependencies import _get_service_token, ORDER_SERVICE_URL

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("order_service.notification_api")

async def check_order_info(user_id: str, order_id: int) -> Dict[str, bool]:
    """
    Проверяет информацию о заказе
    
    Args:
        user_id: ID пользователя
        order_id: ID заказа
        
    Returns:
        Словарь с информацией о заказе
        Если произошла ошибка - возвращает None
    """
    try:
        # perform with retry on 401
        backoffs = [0.5, 1, 2]
        async with httpx.AsyncClient() as client:
            for delay in backoffs:
                token = await _get_service_token()
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{ORDER_SERVICE_URL}/orders/{order_id}/service",
                    headers=headers, timeout=5.0,
                    params={"user_id": user_id}
                )
                if response.status_code == 401:
                    # token expired - clear cache and retry
                    await cache_service.delete("rabbit_service_token")
                    await asyncio.sleep(delay)
                    continue
                break
        
        # now response contains result
        if response.status_code == 200:
            order_data = response.json()
            logger.info("Получена информация о заказе %s для пользователя %s", order_id, user_id)
            return order_data
        elif response.status_code == 404:
            # Настройки не найдены, используем значения по умолчанию
            logger.info("Заказ %s для пользователя %s не найден", order_id, user_id)
            return None
        else:
            logger.warning("Ошибка при получении информации о заказе: %s, %s", response.status_code, response.text)
            return None
                
    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error("Ошибка при запросе информации о заказе: %s", str(e))
        return None
