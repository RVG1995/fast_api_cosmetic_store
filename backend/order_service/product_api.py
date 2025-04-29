"""Модуль для взаимодействия с API сервиса продуктов, включая кэширование и управление запасами."""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import httpx
import redis.asyncio as redis
from redis.exceptions import RedisError
from schema import ProductInfoSchema

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_product_api")

# URL сервиса продуктов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
logger.info("URL сервиса продуктов: %s", PRODUCT_SERVICE_URL)

# Секретный ключ для доступа к API продуктов
INTERNAL_SERVICE_KEY = "test"  # Жестко задаем значение для тестирования
logger.info("Ключ сервиса: '%s'", INTERNAL_SERVICE_KEY)

# Конфигурация Redis для кэширования
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # TTL кэша в секундах (по умолчанию 5 минут)

redis_client = redis.from_url(REDIS_URL)

class ProductAPI:
    """Класс для взаимодействия с API сервиса продуктов"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def get_product(self, product_id: int) -> Optional[ProductInfoSchema]:
        """Получение информации о продукте по ID"""
        cache_key = f"product:{product_id}"
        
        try:
            # Попытка получить данные из кэша
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info("Продукт %d найден в кэше", product_id)
                product_data = json.loads(cached_data)
                return ProductInfoSchema(**product_data)
        except RedisError as e:
            logger.error("Ошибка при чтении из кэша: %s", str(e))
        
        # Запрос к сервису продуктов, если данных нет в кэше
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/products/{product_id}")
                
                if response.status_code == 200:
                    product_data = response.json()
                    
                    # Кэшируем результат
                    try:
                        await redis_client.set(
                            cache_key,
                            json.dumps(product_data),
                            ex=CACHE_TTL
                        )
                    except RedisError as e:
                        logger.error("Ошибка при записи в кэш: %s", str(e))
                    
                    return ProductInfoSchema(**product_data)
                else:
                    logger.warning("Продукт с ID %d не найден, статус: %d", product_id, response.status_code)
                    return None
        except httpx.RequestError as e:
            logger.error("Ошибка при получении продукта %d: %s", product_id, str(e))
            return None
    
    async def check_stock(self, product_id: int, quantity: int) -> Tuple[bool, Optional[ProductInfoSchema]]:
        """
        Проверка наличия товара на складе в нужном количестве
        
        Args:
            product_id: ID товара
            quantity: Требуемое количество
            
        Returns:
            Tuple[bool, Optional[ProductInfoSchema]]: (достаточно ли товара, информация о товаре)
        """
        product = await self.get_product(product_id)
        
        if not product:
            logger.warning("Продукт с ID %d не найден", product_id)
            return False, None
        
        if product.stock < quantity:
            logger.warning(
                "Недостаточное количество товара %d: в наличии %d, запрошено %d",
                product_id, product.stock, quantity
            )
            logger.warning("Недостаточное количество товара %d: в наличии %d, запрошено %d", product_id, product.stock, quantity)
            return False, product
        
        return True, product
    
    async def update_stock(self, product_id: int, quantity_change: int, token: Optional[str] = None) -> bool:
        """
        Обновление количества товара на складе
        
        Args:
            product_id: ID товара
            quantity_change: Изменение количества (отрицательное для уменьшения)
            token: Токен авторизации (опционально для публичного API)
            
        Returns:
            bool: Успешность операции
        """
        from dependencies import _get_service_token
        try:
            async with httpx.AsyncClient() as client:
                # Получаем текущую информацию о продукте
                product = await self.get_product(product_id)
                if not product:
                    logger.warning("Продукт с ID %d не найден для обновления", product_id)
                    return False
                
                # Вычисляем новое количество
                new_stock = max(0, product.stock + quantity_change)
                
                # Инвалидируем кэш до запроса, чтобы быть уверенными, что старые данные не используются
                try:
                    # Удаляем конкретный продукт из кэша
                    await redis_client.delete(f"product:{product_id}")
                    
                    # Инвалидируем списки продуктов, очищаем все ключи, начинающиеся с "products:"
                    cursor = 0
                    while True:
                        cursor, keys = await redis_client.scan(cursor, match="products:*", count=100)
                        if keys:
                            await redis_client.delete(*keys)
                        if cursor == 0:
                            break
                            
                except RedisError as e:
                    logger.error(
                        "Ошибка при предварительной инвалидации кэша для продукта %d: %s",
                        product_id, str(e)
                    )
                backoffs = [0.5, 1, 2]
                # Сначала пробуем использовать публичный API если нужно уменьшить количество
                if quantity_change < 0:
                    for delay in backoffs:
                        token = await _get_service_token()
                        headers = {"Authorization": f"Bearer {token}"}
                        response = await client.put(
                            f"{self.base_url}/products/{product_id}/public-stock",
                            json={"stock": new_stock},
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            logger.info(
                                "Обновлено количество товара %d через публичный API: %d -> %d",
                                product_id, product.stock, new_stock
                            )
                            
                            # Инвалидируем кэш после успешного обновления
                            try:
                                await redis_client.delete(f"product:{product_id}")
                            except RedisError as e:
                                logger.error("Ошибка при инвалидации кэша: %s", str(e))
                            
                            return True
                        if response.status_code == 401:
                    # token expired - clear cache and retry
                            await redis_client.delete("service_token")
                            await asyncio.sleep(delay)
                            continue
                        break
                
                # Если публичный API недоступен или вернул ошибку или нужно увеличить количество, пробуем использовать админский API
                # Это важно для действий администраторов или когда товар нужно пополнить
                logger.info(
                    "Пробуем обновить количество товара %d через админский API",
                    product_id
                )
                for delay in backoffs:
                    token = await _get_service_token()
                    headers = {"Authorization": f"Bearer {token}"}
                    auth_response = await client.put(
                        f"{self.base_url}/products/{product_id}/admin-stock",
                        json={"stock": new_stock, "is_admin_update": True},
                        headers=headers
                    )
                    
                    if auth_response.status_code == 200:
                        logger.info(
                            "Обновлено количество товара %d через админский API: %d -> %d",
                            product_id, product.stock, new_stock
                        )
                        
                        # Инвалидируем кэш после успешного обновления
                        try:
                            await redis_client.delete(f"product:{product_id}")
                        except RedisError as e:
                            logger.error("Ошибка при инвалидации кэша: %s", str(e))
                        
                        return True
                    else:
                        logger.error(
                            "Ошибка при обновлении товара %d через админский API, статус: %d, ответ: %s",
                            product_id, auth_response.status_code, auth_response.text
                        )
                    if response.status_code == 401:
                    # token expired - clear cache and retry
                        await redis_client.delete("service_token")
                        await asyncio.sleep(delay)
                        continue
                    break
                
                # Если все попытки обновления не удались
                logger.error(
                    "Не удалось обновить количество товара %d. Новое количество было бы: %d",
                    product_id, new_stock
                )
                return False
        except (httpx.RequestError, RedisError) as e:
            logger.error(
                "Ошибка при обновлении количества товара %d: %s",
                product_id, str(e)
            )
            return False
    
    async def _get_from_cache(self, product_ids: List[int]) -> Tuple[Dict[int, ProductInfoSchema], List[int]]:
        """Получает продукты из кэша и возвращает найденные и список для последующего запроса"""
        result = {}
        to_fetch = []
        
        for product_id in product_ids:
            cache_key = f"product:{product_id}"
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    result[product_id] = ProductInfoSchema(**json.loads(cached_data))
                else:
                    to_fetch.append(product_id)
            except RedisError as e:
                logger.error("Ошибка при чтении из кэша для продукта %d: %s", product_id, str(e))
                to_fetch.append(product_id)
                
        return result, to_fetch
    
    async def _save_to_cache(self, product_data: dict) -> None:
        """Сохраняет данные продукта в кэш"""
        pid = product_data["id"]
        try:
            await redis_client.set(f"product:{pid}", json.dumps(product_data), ex=CACHE_TTL)
        except RedisError as e:
            logger.error("Ошибка при записи в кэш для продукта %d: %s", pid, str(e))
    
    async def get_products_batch(self, product_ids: List[int], token: Optional[str] = None) -> Dict[int, ProductInfoSchema]:
        """
        Получение информации о нескольких продуктах по ID
        
        Args:
            product_ids: Список ID продуктов
            token: Токен авторизации (опционально для публичного API)
            
        Returns:
            Dict[int, ProductInfoSchema]: Словарь {product_id: продукт}
        """
        # Получаем данные из кэша
        result, products_to_fetch = await self._get_from_cache(product_ids)
        
        if result:
            logger.info("Найдено в кэше %d продуктов из %d", len(result), len(product_ids))
        
        # Если есть что запрашивать из сервиса
        if products_to_fetch:
            try:
                backoffs = [0.5, 1, 2]
                async with httpx.AsyncClient() as client:
                    from dependencies import _get_service_token
                    # Запросим batch-эндпоинт с JWT
                    for attempt, delay in enumerate(backoffs, start=1):
                        token = await _get_service_token()
                        headers = {"Authorization": f"Bearer {token}"}
                        logger.info("get_products_batch: attempt %d, headers=%s", attempt, headers)
                        
                        response = await client.post(
                            f"{self.base_url}/products/batch",
                            json={"product_ids": products_to_fetch},
                            headers=headers,
                            timeout=5.0
                        )
                        
                        logger.info("get_products_batch: status=%d", response.status_code)
                        
                        if response.status_code == 200:
                            for product_data in response.json():
                                pid = product_data["id"]
                                result[pid] = ProductInfoSchema(**product_data)
                                await self._save_to_cache(product_data)
                            break
                            
                        if response.status_code == 401 and attempt < len(backoffs):
                            await asyncio.sleep(delay)
                            continue
                            
                        logger.error(
                            "get_products_batch: unexpected status %d, body=%s",
                            response.status_code, response.text
                        )
                        break
            except httpx.RequestError as e:
                logger.error("Ошибка при получении списка продуктов: %s", str(e))
        
        return result

async def get_product_api() -> ProductAPI:
    """
    Создает и возвращает экземпляр ProductAPI
    
    Returns:
        ProductAPI: Экземпляр API для работы с продуктами
    """
    # Возвращаем экземпляр ProductAPI
    return ProductAPI(base_url=PRODUCT_SERVICE_URL) 