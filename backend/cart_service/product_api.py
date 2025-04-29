"""Модуль для взаимодействия с API сервиса продуктов, включая кэширование в Redis."""

import asyncio
import json
import logging
import os
import pathlib
from typing import Optional, Dict, Any, List

import httpx
from dotenv import load_dotenv
from redis import asyncio as aioredis

from dependencies import _get_service_token

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_api")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Загружаем переменные окружения
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    logger.info("Переменные окружения загружены из %s", env_file)
elif parent_env_file.exists():
    load_dotenv(dotenv_path=parent_env_file)
    logger.info("Переменные окружения загружены из %s", parent_env_file)

# URL сервиса продуктов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
logger.info("URL сервиса продуктов: %s", PRODUCT_SERVICE_URL)

# Секретный ключ для доступа к API продуктов
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")
logger.info("Ключ сервиса: '%s'", INTERNAL_SERVICE_KEY)

class ProductAPI:
    """Класс для взаимодействия с API сервиса продуктов"""
    
    def __init__(self):
        self.base_url = PRODUCT_SERVICE_URL
        self.cache_ttl = int(os.getenv("PRODUCT_CACHE_TTL", "300"))  # TTL кэша в секундах (5 минут по умолчанию)
        self.max_retries = int(os.getenv("API_MAX_RETRIES", "3"))  # Максимальное число повторных попыток
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Redis подключение будет создано асинхронно при первом обращении
        self._redis = None
        
        logger.info("Инициализирован ProductAPI с base_url: %s, cache_ttl: %dс, redis_url: %s", self.base_url, self.cache_ttl, self.redis_url)
    
    async def get_redis(self):
        """Получить или создать подключение к Redis"""
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
                logger.info("Установлено подключение к Redis: %s", self.redis_url)
            except (aioredis.ConnectionError, aioredis.TimeoutError, aioredis.RedisError) as e:
                logger.error("Ошибка подключения к Redis: %s", str(e))
                # Возвращаем None, чтобы вызывающий код мог обработать ситуацию
                return None
        return self._redis
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о продукте по его ID
        
        Args:
            product_id (int): ID продукта
            
        Returns:
            Optional[Dict[str, Any]]: Информация о продукте или None, если продукт не найден
        """
        # Проверяем кэш в Redis
        redis = await self.get_redis()
        cache_key = f"product:{product_id}"
        
        if redis:
            try:
                # Пытаемся получить данные из Redis
                cached_data = await redis.get(cache_key)
                if cached_data:
                    logger.info("Данные о продукте ID=%d получены из Redis кэша", product_id)
                    return json.loads(cached_data)
            except (aioredis.RedisError, json.JSONDecodeError) as e:
                logger.warning("Ошибка при обращении к Redis: %s", str(e))
                # Продолжаем работу, игнорируя ошибку Redis
        
        url = f"{self.base_url}/products/{product_id}"
        logger.info("Запрос информации о продукте ID=%d по URL: %s", product_id, url)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=10.0)
                    
                    if response.status_code == 200:
                        product_data = response.json()
                        logger.info("Получена информация о продукте ID=%d", product_id)
                        
                        # Кэшируем в Redis, если подключение доступно
                        if redis:
                            try:
                                await redis.setex(
                                    cache_key,
                                    self.cache_ttl,
                                    json.dumps(product_data)
                                )
                                logger.debug("Данные о продукте ID=%d сохранены в Redis кэш", product_id)
                            except (aioredis.RedisError, TypeError) as e:
                                logger.warning("Ошибка при сохранении в Redis: %s", str(e))
                        
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
            except (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
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
        
        # Получаем подключение к Redis
        redis = await self.get_redis()
        
        # Хранилище для ID, которые нужно запросить у API
        to_fetch_ids = []
        
        # Если Redis доступен, проверяем данные в кэше
        if redis:
            try:
                # Формируем ключи для продуктов
                cache_keys = [f"product:{pid}" for pid in unique_product_ids]
                
                # Делаем массовый запрос к Redis через MGET
                cached_values = await redis.mget(cache_keys)
                
                # Обрабатываем результаты запроса
                for i, value in enumerate(cached_values):
                    if value:
                        # Если значение найдено в кэше, разбираем JSON и добавляем в результат
                        product_data = json.loads(value)
                        product_id = unique_product_ids[i]
                        result[product_id] = product_data
                        logger.debug("Данные о продукте ID=%d получены из Redis кэша", product_id)
                    else:
                        # Если значение не найдено, добавляем ID в список для запроса к API
                        to_fetch_ids.append(unique_product_ids[i])
                
                logger.info("Получено %d продуктов из кэша, осталось запросить %d", len(result), len(to_fetch_ids))
            except (aioredis.RedisError, json.JSONDecodeError) as e:
                logger.warning("Ошибка при обращении к Redis: %s", str(e))
                # В случае ошибки, запрашиваем все ID
                to_fetch_ids = unique_product_ids
        else:
            # Если Redis недоступен, запрашиваем все ID
            to_fetch_ids = unique_product_ids
        
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
                            
                            # Сохраняем результаты в Redis и добавляем в итоговый словарь
                            for product_data in batch_data:
                                product_id = product_data.get("id")
                                if product_id:
                                    # Добавляем в результат
                                    result[product_id] = product_data
                                    
                                    # Сохраняем в Redis, если подключение доступно
                                    if redis:
                                        try:
                                            cache_key = f"product:{product_id}"
                                            await redis.setex(
                                                cache_key,
                                                self.cache_ttl,
                                                json.dumps(product_data)
                                            )
                                        except (aioredis.RedisError, TypeError) as e:
                                            logger.warning("Ошибка при сохранении в Redis: %s", str(e))
                            
                            # Если все ID были успешно получены, возвращаем результат
                            if all(pid in result for pid in to_fetch_ids):
                                return result
                            
                            # Иначе обновляем список ID для запроса
                            to_fetch_ids = [pid for pid in to_fetch_ids if pid not in result]
                            logger.info("Осталось получить данные для %d продуктов индивидуально", len(to_fetch_ids))
                        if response.status_code == 401:
                            # token expired - clear cache and retry
                            redis = await self.get_redis()
                            if redis:
                                await redis.delete("service_token")
                            await asyncio.sleep(delay)
                            continue
                        break
            except (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
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
        if self._redis:
            await self._redis.close()
            logger.info("Соединение с Redis закрыто") 