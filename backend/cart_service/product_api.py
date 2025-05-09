"""API для взаимодействия с сервисом продуктов."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
import httpx

from config import settings
from dependencies import _get_service_token
from cache import cache_service

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_api")

# URL сервиса продуктов из конфигурации
PRODUCT_SERVICE_URL = settings.PRODUCT_SERVICE_URL
logger.info("URL сервиса продуктов: %s", PRODUCT_SERVICE_URL)


class ProductAPI:
    """Класс для взаимодействия с API сервиса продуктов"""
    
    def __init__(self):
        self.base_url = PRODUCT_SERVICE_URL
        self.cache_ttl = settings.PRODUCT_CACHE_TTL  # TTL кэша в секундах
        self.max_retries = settings.API_MAX_RETRIES  # Максимальное число повторных попыток
        
        logger.info("Инициализирован ProductAPI с base_url: %s, cache_ttl: %dс", self.base_url, self.cache_ttl)
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о продукте по его ID
        
        Args:
            product_id (int): ID продукта
            
        Returns:
            Optional[Dict[str, Any]]: Информация о продукте или None, если продукт не найден
        """
        # Проверяем кэш 
        cache_key = f"product:{product_id}"
        
        # Пытаемся получить данные из кэша
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            logger.info("Данные о продукте ID=%d получены из кэша", product_id)
            return cached_data
        
        url = f"{self.base_url}/products/{product_id}"
        logger.info("Запрос информации о продукте ID=%d по URL: %s", product_id, url)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=10.0)
                    
                    if response.status_code == 200:
                        product_data = response.json()
                        logger.info("Получена информация о продукте ID=%d", product_id)
                        
                        # Кэшируем в Redis
                        await cache_service.set(cache_key, product_data, self.cache_ttl)
                        logger.debug("Данные о продукте ID=%d сохранены в кэш", product_id)
                        
                        return product_data
                    elif response.status_code == 404:
                        logger.warning("Продукт с ID=%d не найден", product_id)
                        return None
                    else:
                        logger.error("Ошибка при получении продукта: %d - %s", response.status_code, response.text)
                        if attempt < self.max_retries - 1:
                            # Если это не последняя попытка, то подождем перед следующей
                            retry_delay = 0.5 * (2 ** attempt)  # Экспоненциальный backoff
                            logger.info("Повторная попытка через %f секунд...", retry_delay)
                            await asyncio.sleep(retry_delay)
                        else:
                            return None
            except (httpx.RequestError, httpx.ConnectError, httpx.TimeoutException) as e:
                logger.error("Исключение при запросе к API продуктов: %s", str(e))
                if attempt < self.max_retries - 1:
                    retry_delay = 0.5 * (2 ** attempt)
                    logger.info("Повторная попытка через %f секунд...", retry_delay)
                    await asyncio.sleep(retry_delay)
                else:
                    return None
        
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
    
    async def get_products_info(self, product_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Получает информацию о нескольких продуктах по их ID
        
        Args:
            product_ids (List[int]): Список ID продуктов
            
        Returns:
            Dict[int, Dict[str, Any]]: Словарь с информацией о продуктах, где ключ - ID продукта
        """
        result = {}
        
        # Если список ID пустой, сразу возвращаем пустой словарь
        if not product_ids:
            logger.info("Пустой список ID продуктов, возвращаем пустой словарь")
            return result
        
        # Убираем дубликаты ID
        unique_product_ids = list(set(product_ids))
        logger.info("Получение информации о %d уникальных продуктах", len(unique_product_ids))
        
        # Хранилище для ID, которые нужно запросить у API
        to_fetch_ids = []
        
        # Проверяем кэш для каждого ID продукта
        for product_id in unique_product_ids:
            cache_key = f"product:{product_id}"
            cached_data = await cache_service.get(cache_key)
            
            if cached_data:
                result[product_id] = cached_data
                logger.debug("Данные о продукте ID=%d получены из кэша", product_id)
            else:
                to_fetch_ids.append(product_id)
        
        logger.info("Получено %d продуктов из кэша, осталось запросить %d", len(result), len(to_fetch_ids))
        
        # Если остались ID для запроса
        if to_fetch_ids:
            backoffs = [0.5, 1, 2]
            # Попробуем сначала сделать пакетный запрос для всех продуктов
            try:
                batch_url = f"{self.base_url}/products/batch"
                logger.info("Попытка пакетного запроса для %d продуктов", len(to_fetch_ids))
                
                async with httpx.AsyncClient() as client:
                    for delay in backoffs:
                    # Добавляем заголовок service-key для авторизации
                        token = await _get_service_token()
                        headers = {"Authorization": f"Bearer {token}"}
                        
                        response = await client.post(
                            batch_url, 
                            json={"product_ids": to_fetch_ids}, 
                            headers=headers,
                            timeout=15.0
                        )
                        
                        if response.status_code == 200:
                            batch_data = response.json()
                            logger.info("Успешно получены данные для %d продуктов в пакетном запросе", len(batch_data))
                            
                            # Сохраняем результаты в кэш и добавляем в итоговый словарь
                            for product_data in batch_data:
                                product_id = product_data.get("id")
                                if product_id:
                                    # Добавляем в результат
                                    result[product_id] = product_data
                                    
                                    # Сохраняем в кэш
                                    cache_key = f"product:{product_id}"
                                    await cache_service.set(cache_key, product_data, self.cache_ttl)
                            
                            # Если все ID были успешно получены, возвращаем результат
                            if all(pid in result for pid in to_fetch_ids):
                                return result
                            
                            # Иначе обновляем список ID для запроса
                            to_fetch_ids = [pid for pid in to_fetch_ids if pid not in result]
                            logger.info("Осталось получить данные для %d продуктов индивидуально", len(to_fetch_ids))
                        if response.status_code == 401:
                            # token expired - clear cache and retry
                            await cache_service.delete("service_token_cart")
                            await asyncio.sleep(delay)
                            continue
                        break
            except (httpx.RequestError, httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                logger.warning("Ошибка при выполнении пакетного запроса: %s", str(e))
                # Продолжаем с индивидуальными запросами
            
            # Если пакетный запрос не поддерживается или не все данные были получены,
            # делаем параллельные запросы для оставшихся ID
            if to_fetch_ids:
                logger.info("Выполнение %d параллельных запросов для продуктов", len(to_fetch_ids))
                tasks = [self.get_product_by_id(pid) for pid in to_fetch_ids]
                products = await asyncio.gather(*tasks)
                
                # Заполняем результат
                for i, product in enumerate(products):
                    if product:
                        result[to_fetch_ids[i]] = product
        
        return result
        
    async def close(self):
        """Закрывает соединение с Redis при завершении работы"""
        # Нет необходимости закрывать соединение, так как используем общий CacheService
        pass
