import httpx
import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import pathlib

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_api")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info(f"Загружаем .env из {env_file}")
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    logger.info(f"Загружаем .env из {parent_env_file}")
    load_dotenv(dotenv_path=parent_env_file)
else:
    logger.warning("Файл .env не найден!")

class ProductAPI:
    """Класс для взаимодействия с API сервиса продуктов"""
    
    def __init__(self):
        self.base_url = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
        logger.info(f"Инициализирован ProductAPI с base_url: {self.base_url}")
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о продукте по его ID
        
        Args:
            product_id (int): ID продукта
            
        Returns:
            Optional[Dict[str, Any]]: Информация о продукте или None, если продукт не найден
        """
        url = f"{self.base_url}/products/{product_id}"
        logger.info(f"Запрос информации о продукте ID={product_id} по URL: {url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    product_data = response.json()
                    logger.info(f"Получена информация о продукте ID={product_id}")
                    return product_data
                elif response.status_code == 404:
                    logger.warning(f"Продукт с ID={product_id} не найден")
                    return None
                else:
                    logger.error(f"Ошибка при получении продукта: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Исключение при запросе к API продуктов: {str(e)}")
            return None
    
    async def check_product_stock(self, product_id: int, quantity: int) -> Dict[str, Any]:
        """
        Проверяет, достаточно ли товара на складе
        
        Args:
            product_id (int): ID продукта
            quantity (int): Количество, которое нужно проверить
            
        Returns:
            Dict[str, Any]: Результат проверки с полями:
                - success (bool): Можно ли добавить указанное количество товара
                - available_stock (int): Доступное количество товара
                - error (str, optional): Сообщение об ошибке, если есть
        """
        product = await self.get_product_by_id(product_id)
        
        if not product:
            return {
                "success": False,
                "available_stock": 0,
                "error": "Продукт не найден"
            }
        
        available_stock = product.get("stock", 0)
        
        if available_stock >= quantity:
            return {
                "success": True,
                "available_stock": available_stock
            }
        else:
            return {
                "success": False,
                "available_stock": available_stock,
                "error": f"Недостаточно товара на складе. Доступно: {available_stock}"
            }
    
    async def get_products_info(self, product_ids: list[int]) -> Dict[int, Dict[str, Any]]:
        """
        Получает информацию о нескольких продуктах по их ID
        
        Args:
            product_ids (list[int]): Список ID продуктов
            
        Returns:
            Dict[int, Dict[str, Any]]: Словарь с информацией о продуктах, где ключ - ID продукта
        """
        result = {}
        
        # Если список ID пустой, сразу возвращаем пустой словарь
        if not product_ids:
            logger.info("Пустой список ID продуктов, возвращаем пустой словарь")
            return result
        
        # Пакетный запрос за всеми продуктами был бы эффективнее,
        # но для простоты делаем отдельные запросы
        for product_id in product_ids:
            product = await self.get_product_by_id(product_id)
            if product:
                result[product_id] = product
        
        return result 