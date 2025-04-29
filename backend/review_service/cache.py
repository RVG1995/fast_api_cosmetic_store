"""
Модуль кэша для review_service: функции взаимодействия с Redis.
"""

import os
import json
import logging
from typing import Any, Optional
from redis.asyncio import Redis
from dotenv import load_dotenv
import redis

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_service.cache")

# Получаем параметры подключения к Redis из переменных окружения
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REVIEW_REDIS_DB", "3"))  # Используем базу 3 для сервиса отзывов
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Создаем клиент Redis
redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,  # Декодируем ответы в строки
    socket_timeout=5,
)

# Время жизни кэша в секундах
CACHE_TTL = {
    "review": 3600,  # 1 час для отдельного отзыва
    "reviews": 1800,  # 30 минут для списков отзывов
    "statistics": 3600,  # 1 час для статистики
    "permissions": 300,  # 5 минут для проверки разрешений пользователя
}

# Префиксы ключей кэша
CACHE_KEYS = {
    "review": "review_service:review:",
    "product_reviews": "review_service:product_reviews:",
    "store_reviews": "review_service:store_reviews:",
    "user_reviews": "review_service:user_reviews:",
    "permissions": "review_service:permissions:",
    "product_statistics": "review_service:product_statistics:",
    "store_statistics": "review_service:store_statistics:",
    "product_review_stats": "review_service:product_review_stats:",
    "store_review_stats": "review_service:store_review_stats:",
    "test": "review_service:test:",
    "product_batch_statistics": "product_batch_stats:",
    "review_detail": "review_detail:"
}

async def initialize_redis() -> None:
    """Проверяем текущее соединение без reassignment."""
    try:
        await redis_client.ping()
        logger.info("Подключение к Redis OK")
    except Exception as e:
        logger.error("Ошибка при подключении к Redis: %s", e)

async def close_redis_connection() -> None:
    """Закрытие соединения с Redis"""
    if redis_client:
        await redis_client.close()
        logger.info("Соединение с Redis закрыто")

async def cache_get(key: str) -> Optional[Any]:
    """
    Получение данных из кэша по ключу
    
    Args:
        key: Ключ кэша
        
    Returns:
        Данные из кэша или None, если кэш не найден
    """
    try:
        data = await redis_client.get(key)
        if data:
            logger.debug("Получены данные из кэша: %s", key)
            result = json.loads(data)
            # Исправляем устаревшие ключи в данных из кэша
            if isinstance(result, dict):
                if "avg_rating" in result and "average_rating" not in result:
                    result["average_rating"] = result.pop("avg_rating")
                if "rating_counts" in result:
                    # Преобразование строковых ключей в целочисленные
                    if any(isinstance(k, str) for k in result["rating_counts"].keys()):
                        result["rating_counts"] = {int(k): v for k, v in result["rating_counts"].items()}
            return result
        logger.debug("Кэш не найден: %s", key)
        return None
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.error("Ошибка при получении данных из кэша: %s", e)
        return None

async def cache_set(key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """
    Сохранение данных в кэш по ключу
    
    Args:
        key: Ключ кэша
        data: Данные для сохранения
        ttl: Время жизни кэша в секундах
        
    Returns:
        bool: True если данные успешно сохранены, иначе False
    """
    try:
        # Преобразуем данные в JSON-строку
        json_data = json.dumps(data)
        # Сохраняем данные в кэш
        if ttl:
            await redis_client.setex(key, ttl, json_data)
        else:
            await redis_client.set(key, json_data)
        logger.debug("Данные сохранены в кэш: %s", key)
        return True
    except (redis.RedisError, TypeError) as e:
        logger.error("Ошибка при сохранении данных в кэш: %s", e)
        return False

async def cache_delete(key: str) -> bool:
    """
    Удаление данных из кэша по ключу
    
    Args:
        key: Ключ кэша
        
    Returns:
        bool: True если данные успешно удалены, иначе False
    """
    try:
        await redis_client.delete(key)
        logger.debug("Данные удалены из кэша: %s", key)
        return True
    except redis.RedisError as e:
        logger.error("Ошибка при удалении данных из кэша: %s", e)
        return False

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удаление данных из кэша по шаблону ключа
    
    Args:
        pattern: Шаблон ключа
        
    Returns:
        bool: True если данные успешно удалены, иначе False
    """
    try:
        # Получаем все ключи, соответствующие шаблону
        cursor = 0
        deleted_count = 0
        
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                deleted_count += await redis_client.delete(*keys)
            if cursor == 0:
                break
                
        logger.debug("Удалено %d ключей по шаблону: %s", deleted_count, pattern)
        return True
    except redis.RedisError as e:
        logger.error("Ошибка при удалении данных из кэша по шаблону: %s", e)
        return False

async def invalidate_review_cache(review_id: int) -> bool:
    """
    Инвалидация кэша для конкретного отзыва
    
    Args:
        review_id: ID отзыва
        
    Returns:
        bool: True если кэш успешно инвалидирован, иначе False
    """
    try:
        # Получаем данные отзыва, чтобы узнать product_id
        from models import ReviewModel
        from database import get_session
        
        # Используем новую сессию для получения данных отзыва
        session = await anext(get_session())
        review = await ReviewModel.get_by_id(session, review_id)
        
        # Удаляем кэш конкретного отзыва
        key = f"{CACHE_KEYS['review']}{review_id}"
        await cache_delete(key)
        
        # Инвалидируем списки отзывов
        await cache_delete_pattern(f"{CACHE_KEYS['product_reviews']}*")
        await cache_delete_pattern(f"{CACHE_KEYS['store_reviews']}*")
        await cache_delete_pattern(f"{CACHE_KEYS['user_reviews']}*")
        
        # Инвалидируем статистику
        await cache_delete_pattern(f"{CACHE_KEYS['product_statistics']}*")
        await cache_delete_pattern(f"{CACHE_KEYS['store_statistics']}*")
        
        # Инвалидируем кэш пакетных запросов статистики
        await cache_delete_pattern(f"{CACHE_KEYS['product_batch_statistics']}*")
        
        # Если отзыв относится к товару, инвалидируем статистику этого товара
        if review and review.product_id:
            await cache_delete(f"{CACHE_KEYS['product_statistics']}{review.product_id}")
            
            # Инвалидируем все пакетные запросы, которые могут включать этот товар
            keys_to_check = await redis_client.keys(f"{CACHE_KEYS['product_batch_statistics']}*")
            for key in keys_to_check:
                # Проверяем, содержит ли ключ ID товара
                product_id_str = str(review.product_id)
                # Если ключ включает ID товара (например, в списке ID через запятую)
                if product_id_str in key:
                    await cache_delete(key)
                    
        logger.info("Кэш отзыва %d и связанных списков инвалидирован", review_id)
        return True
    except (redis.RedisError, ImportError, AttributeError) as e:
        logger.error("Ошибка при инвалидации кэша отзыва: %s", e)
        return False

async def invalidate_product_reviews_cache(product_id: int) -> bool:
    """
    Инвалидация кэша отзывов для конкретного товара
    
    Args:
        product_id: ID товара
        
    Returns:
        bool: True если кэш успешно инвалидирован, иначе False
    """
    try:
        # Удаляем кэш списков отзывов для товара
        await cache_delete_pattern(f"{CACHE_KEYS['product_reviews']}{product_id}:*")
        
        # Инвалидируем статистику товара
        await cache_delete(f"{CACHE_KEYS['product_statistics']}{product_id}")
        await cache_delete(f"{CACHE_KEYS['product_review_stats']}{product_id}")
        
        # Инвалидируем все пакетные запросы, которые могут включать этот товар
        keys_to_check = await redis_client.keys(f"{CACHE_KEYS['product_batch_statistics']}*")
        product_id_str = str(product_id)
        
        for key in keys_to_check:
            # Проверяем, содержит ли ключ ID товара
            if product_id_str in key:
                await cache_delete(key)
        
        logger.info("Кэш отзывов для товара %d и связанных пакетных запросов инвалидирован", product_id)
        return True
    except redis.RedisError as e:
        logger.error("Ошибка при инвалидации кэша отзывов для товара: %s", e)
        return False

async def invalidate_store_reviews_cache() -> bool:
    """
    Инвалидация кэша отзывов для магазина
    
    Returns:
        bool: True если кэш успешно инвалидирован, иначе False
    """
    # Удаляем кэш списков отзывов для магазина
    await cache_delete_pattern(f"{CACHE_KEYS['store_reviews']}*")
    
    # Инвалидируем статистику магазина
    await cache_delete(f"{CACHE_KEYS['store_statistics']}stats")
    
    logger.info("Кэш отзывов для магазина инвалидирован")
    return True

async def invalidate_user_reviews_cache(user_id: int) -> bool:
    """
    Инвалидация кэша отзывов для конкретного пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если кэш успешно инвалидирован, иначе False
    """
    # Удаляем кэш списков отзывов для пользователя
    await cache_delete_pattern(f"{CACHE_KEYS['user_reviews']}{user_id}:*")
    
    # Инвалидируем разрешения пользователя
    await cache_delete_pattern(f"{CACHE_KEYS['permissions']}{user_id}:*")
    
    logger.info("Кэш отзывов для пользователя %d инвалидирован", user_id)
    return True
