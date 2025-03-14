import httpx
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from fastapi import Depends, HTTPException, status

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_cart_api")

# URL сервиса корзины
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8002")
logger.info(f"URL сервиса корзины: {CART_SERVICE_URL}")

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
                response = await client.get(f"{CART_SERVICE_URL}/cart", params={"id": cart_id})
                
                if response.status_code == 200:
                    cart_data = response.json()
                    
                    # Если указан user_id, проверяем, что корзина принадлежит этому пользователю
                    if user_id is not None and cart_data.get("user_id") != user_id:
                        logger.warning(f"Корзина {cart_id} не принадлежит пользователю {user_id}")
                        return None
                    
                    return cart_data
                else:
                    logger.warning(f"Корзина с ID {cart_id} не найдена, статус: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении корзины {cart_id}: {str(e)}")
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
                response = await client.delete(f"{CART_SERVICE_URL}/cart", params={"id": cart_id})
                
                if response.status_code in (200, 204):
                    logger.info(f"Корзина {cart_id} успешно очищена")
                    return True
                else:
                    logger.error(f"Ошибка при очистке корзины {cart_id}, статус: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при очистке корзины {cart_id}: {str(e)}")
            return False

async def get_cart_api() -> CartAPI:
    """Dependency для получения экземпляра CartAPI"""
    return CartAPI() 