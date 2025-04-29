"""Модуль для взаимодействия с API сервиса корзины.

Этот модуль предоставляет класс CartAPI для работы с корзиной пользователя,
включая получение информации о корзине и её очистку после создания заказа.
"""

import logging
import os
from typing import Dict, Optional, Any

import httpx

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_cart_api")

# URL сервиса корзины
CART_SERVICE_URL = os.getenv(
    "CART_SERVICE_URL", 
    "http://localhost:8002"
)
logger.info("URL сервиса корзины: %s", CART_SERVICE_URL)

class CartAPI:
    """Класс для взаимодействия с API сервиса корзины"""
    
    async def get_cart(self, cart_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Получение информации о корзине по ID
        
        Args:
            cart_id: ID корзины
            user_id: ID пользователя для проверки (если указан)
            
        Returns:
            Dict[str, Any]: Данные корзины или None, если не найдена
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CART_SERVICE_URL}/cart",
                    params={"id": cart_id}
                )
                
                if response.status_code == 200:
                    cart_data = response.json()
                    
                    # Если указан user_id, проверяем, что корзина принадлежит этому пользователю
                    if user_id is not None and cart_data.get("user_id") != user_id:
                        logger.warning("Корзина %d не принадлежит пользователю %d",
                        cart_id, user_id)
                        return None
                    
                    return cart_data
                else:
                    logger.warning("Корзина с ID %d не найдена, статус: %d", cart_id, response.status_code)
                    return None
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            logger.error("Ошибка при получении корзины %d: %s", cart_id, str(e))
            return None
    
    async def clear_cart(self, cart_id: int) -> bool:
        """
        Очистка корзины после создания заказа
        
        Args:
            cart_id: ID корзины
            
        Returns:
            bool: Успешность операции
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{CART_SERVICE_URL}/cart",
                    params={"id": cart_id}
                )
                
                if response.status_code in (200, 204):
                    logger.info("Корзина %d успешно очищена", cart_id)
                    return True
                else:
                    logger.error(
                        "Ошибка при очистке корзины %d, статус: %d", 
                        cart_id,
                        response.status_code
                    )
                    return False
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(
                "Ошибка при очистке корзины %d: %s", 
                cart_id,
                str(e)
            )
            return False

async def get_cart_api() -> CartAPI:
    """Dependency для получения экземпляра CartAPI"""
    return CartAPI()
