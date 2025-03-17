import httpx
import os
import logging
import json
from typing import Dict, List, Optional, Tuple
from schema import ProductInfoSchema
import redis.asyncio as redis
from fastapi import Depends

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_product_api")

# URL сервиса продуктов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
logger.info(f"URL сервиса продуктов: {PRODUCT_SERVICE_URL}")

# Секретный ключ для доступа к API продуктов
INTERNAL_SERVICE_KEY = "test"  # Жестко задаем значение для тестирования
logger.info(f"Ключ сервиса: '{INTERNAL_SERVICE_KEY}'")

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
                logger.info(f"Продукт {product_id} найден в кэше")
                product_data = json.loads(cached_data)
                return ProductInfoSchema(**product_data)
        except Exception as e:
            logger.error(f"Ошибка при чтении из кэша: {str(e)}")
        
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
                    except Exception as e:
                        logger.error(f"Ошибка при записи в кэш: {str(e)}")
                    
                    return ProductInfoSchema(**product_data)
                else:
                    logger.warning(f"Продукт с ID {product_id} не найден, статус: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении продукта {product_id}: {str(e)}")
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
            logger.warning(f"Продукт с ID {product_id} не найден")
            return False, None
        
        if product.stock < quantity:
            logger.warning(f"Недостаточное количество товара {product_id}: в наличии {product.stock}, запрошено {quantity}")
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
        try:
            async with httpx.AsyncClient() as client:
                # Получаем текущую информацию о продукте
                product = await self.get_product(product_id)
                if not product:
                    logger.warning(f"Продукт с ID {product_id} не найден для обновления")
                    return False
                
                # Вычисляем новое количество
                new_stock = max(0, product.stock + quantity_change)
                
                # Настраиваем заголовки с секретным ключом и авторизацией, если доступна
                headers = {
                    "service-key": INTERNAL_SERVICE_KEY  # Добавляем секретный ключ (с маленькой буквы!)
                }
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                
                # Используем публичный API с секретным ключом для обновления количества
                response = await client.put(
                    f"{self.base_url}/products/{product_id}/public-stock",
                    json={"stock": new_stock},
                    headers=headers
                )
                
                # Если публичный API успешно обработал запрос
                if response.status_code == 200:
                    logger.info(f"Обновлено количество товара {product_id} через публичный API: {product.stock} -> {new_stock}")
                    
                    # Инвалидируем кэш
                    try:
                        await redis_client.delete(f"product:{product_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при инвалидации кэша: {str(e)}")
                    
                    return True
                
                # Если публичный API недоступен или вернул ошибку, пробуем использовать API с авторизацией
                # Это важно для действий администраторов или когда товар нужно пополнить
                if token and response.status_code != 200:
                    logger.info(f"Пробуем обновить количество товара {product_id} через API с авторизацией")
                    
                    auth_response = await client.put(
                        f"{self.base_url}/products/{product_id}/stock",
                        json={"stock": new_stock},
                        headers=headers
                    )
                    
                    if auth_response.status_code == 200:
                        logger.info(f"Обновлено количество товара {product_id} через API с авторизацией: {product.stock} -> {new_stock}")
                        
                        # Инвалидируем кэш
                        try:
                            await redis_client.delete(f"product:{product_id}")
                        except Exception as e:
                            logger.error(f"Ошибка при инвалидации кэша: {str(e)}")
                        
                        return True
                    else:
                        logger.error(f"Ошибка при обновлении товара {product_id} через API с авторизацией, статус: {auth_response.status_code}, ответ: {auth_response.text}")
                
                # Если все попытки обновления не удались
                logger.error(f"Не удалось обновить количество товара {product_id}, статус: {response.status_code}, ответ: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества товара {product_id}: {str(e)}")
            return False
    
    async def get_products_batch(self, product_ids: List[int], token: Optional[str] = None) -> Dict[int, ProductInfoSchema]:
        """
        Получение информации о нескольких продуктах по ID
        
        Args:
            product_ids: Список ID продуктов
            token: Токен авторизации (опционально для публичного API)
            
        Returns:
            Dict[int, ProductInfoSchema]: Словарь {product_id: продукт}
        """
        result = {}
        cache_hits = []
        products_to_fetch = []
        
        # Пытаемся получить данные из кэша
        for product_id in product_ids:
            cache_key = f"product:{product_id}"
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    product_data = json.loads(cached_data)
                    result[product_id] = ProductInfoSchema(**product_data)
                    cache_hits.append(product_id)
                else:
                    products_to_fetch.append(product_id)
            except Exception as e:
                logger.error(f"Ошибка при чтении из кэша для продукта {product_id}: {str(e)}")
                products_to_fetch.append(product_id)
        
        if cache_hits:
            logger.info(f"Найдено в кэше {len(cache_hits)} продуктов из {len(product_ids)}")
        
        # Если есть что запрашивать из сервиса
        if products_to_fetch:
            try:
                async with httpx.AsyncClient() as client:
                    # Настраиваем заголовки для авторизации и секретный ключ сервиса
                    headers = {
                        "service-key": INTERNAL_SERVICE_KEY  # Добавляем секретный ключ (с маленькой буквы!)
                    }
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    
                    logger.info(f"Запрос на /products/public-batch с заголовками: {headers}")
                    logger.info(f"Service-Key: '{INTERNAL_SERVICE_KEY}'")
                
                    # Используем публичный эндпоинт с секретным ключом
                    response = await client.post(
                        f"{self.base_url}/products/public-batch",
                        json={"product_ids": products_to_fetch},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        products_data = response.json()
                        
                        for product_data in products_data:
                            product_id = product_data["id"]
                            product = ProductInfoSchema(**product_data)
                            result[product_id] = product
                            
                            # Кэшируем результат
                            try:
                                cache_key = f"product:{product_id}"
                                await redis_client.set(
                                    cache_key, 
                                    json.dumps(product_data), 
                                    ex=CACHE_TTL
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при записи в кэш для продукта {product_id}: {str(e)}")
                    else:
                        logger.error(f"Ошибка при получении списка продуктов через /public-batch, статус: {response.status_code}, ответ: {response.text}")
                        
                        # Пробуем использовать обычный API с ключом сервиса, даже если нет токена
                        logger.info("Пробуем получить данные через API /batch с ключом сервиса")
                        # Выводим stack trace для отладки
                        import traceback
                        logger.info(f"DEBUG: Текущий контекст - stack trace: {traceback.format_stack()}")
                        logger.info(f"Запрос на /products/batch с заголовками: {headers}")
                        # Проверяем содержимое заголовков именно перед отправкой
                        logger.info(f"DEBUG: Заголовки для /products/batch - service-key: '{headers.get('service-key')}'")
                        
                        # Пробуем с заглавной буквы (как в оригинале)
                        batch_headers = {
                            "Service-Key": INTERNAL_SERVICE_KEY  # С большой буквы
                        }
                        if token:
                            batch_headers["Authorization"] = f"Bearer {token}"
                        
                        logger.info(f"Новые заголовки для /products/batch: {batch_headers}")
                        
                        auth_response = await client.post(
                            f"{self.base_url}/products/batch",
                            json={"product_ids": products_to_fetch},
                            headers=batch_headers  # Используем новые заголовки
                        )
                        
                        if auth_response.status_code == 200:
                            auth_products_data = auth_response.json()
                            
                            for product_data in auth_products_data:
                                product_id = product_data["id"]
                                product = ProductInfoSchema(**product_data)
                                result[product_id] = product
                                
                                # Кэшируем результат
                                try:
                                    cache_key = f"product:{product_id}"
                                    await redis_client.set(
                                        cache_key, 
                                        json.dumps(product_data), 
                                        ex=CACHE_TTL
                                    )
                                except Exception as e:
                                    logger.error(f"Ошибка при записи в кэш для продукта {product_id}: {str(e)}")
                        else:
                            logger.error(f"Ошибка при получении списка продуктов через авторизованный API, статус: {auth_response.status_code}")
                        
            except Exception as e:
                logger.error(f"Ошибка при получении списка продуктов: {str(e)}")
        
        return result

async def get_product_api() -> ProductAPI:
    """
    Создает и возвращает экземпляр ProductAPI
    
    Returns:
        ProductAPI: Экземпляр API для работы с продуктами
    """
    # Возвращаем экземпляр ProductAPI
    return ProductAPI(base_url=PRODUCT_SERVICE_URL) 