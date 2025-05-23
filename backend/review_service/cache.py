import json
import hashlib
import datetime
from typing import Any, Dict, List, Optional, Union, Callable
import redis.asyncio as redis
from functools import wraps

from config import settings, get_redis_url, get_cache_ttl, get_cache_keys, logger

# Настройки кэширования из конфигурации
CACHE_ENABLED = settings.CACHE_ENABLED
CACHE_TTL = get_cache_ttl()
CACHE_KEYS = get_cache_keys()

# Добавляем ключ для кэширования прав пользователей, если его нет
if 'user_permissions' not in CACHE_KEYS:
    CACHE_KEYS['user_permissions'] = 'user_permissions:'

# Функция для сериализации datetime объектов и других сложных типов в JSON
def json_serial(obj):
    """Сериализатор для объектов, которые не поддерживаются стандартным JSON"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    # Обработка ORM объектов, у которых есть id
    if hasattr(obj, 'id') and callable(getattr(obj, '__dict__', None)):
        # Возвращаем словарь с id объекта
        return {'id': obj.id}
    # Для других неизвестных типов просто преобразуем в строку
    try:
        return str(obj)
    except:
        return None

class CacheService:
    """Сервис кэширования данных с использованием Redis"""
    
    def __init__(self):
        """Инициализация сервиса кэширования"""
        self.enabled = CACHE_ENABLED
        self.redis = None
            
        if not self.enabled:
            logger.info("Кэширование отключено в настройках")
            return
            
        logger.info("Кэширование включено, инициализация соединения с Redis")
    
    async def initialize(self):
        """Асинхронная инициализация соединения с Redis"""
        if not self.enabled:
            return
            
        try:
            # Получаем URL подключения к Redis из конфигурации
            redis_url = get_redis_url()
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,  # Декодируем ответы в строки
                socket_timeout=5,
            )
            
            logger.info(f"Подключение к Redis для кэширования успешно: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error(f"Ошибка подключения к Redis для кэширования: {str(e)}")
            self.redis = None
            self.enabled = False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кэша по ключу
        
        Args:
            key: Ключ кэша
            
        Returns:
            Optional[Any]: Значение из кэша или None, если ключ не найден
        """
        if not self.enabled or not self.redis:
            return None
            
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug(f"Получены данные из кэша: {key}")
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
            logger.debug(f"Кэш не найден: {key}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении данных из кэша: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохраняет значение в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни ключа в секундах
            
        Returns:
            bool: True при успешном сохранении, иначе False
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            # Преобразуем данные в JSON-строку с поддержкой datetime
            json_data = json.dumps(value, default=json_serial)
            # Сохраняем данные в кэш
            if ttl:
                await self.redis.setex(key, ttl, json_data)
            else:
                await self.redis.set(key, json_data)
            logger.debug(f"Данные сохранены в кэш: {key}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в кэш: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Удаляет ключ из кэша
        
        Args:
            key: Ключ для удаления
            
        Returns:
            bool: True при успешном удалении, иначе False
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            await self.redis.delete(key)
            logger.debug(f"Данные удалены из кэша: {key}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении ключа из кэша: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "review:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        if not self.enabled or not self.redis:
            return 0
            
        try:
            # Получаем все ключи, соответствующие шаблону
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += await self.redis.delete(*keys)
                if cursor == 0:
                    break
                    
            logger.debug(f"Удалено {deleted_count} ключей по шаблону: {pattern}")
            return deleted_count
        except Exception as e:
            logger.error(f"Ошибка при удалении ключей по шаблону: {str(e)}")
            return 0
    
    def get_key_for_function(self, prefix: str, *args, **kwargs) -> str:
        """
        Формирует ключ кэша для функции на основе аргументов
        
        Args:
            prefix: Префикс ключа (обычно имя функции)
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            str: Ключ кэша
        """
        # Создаем хеш от аргументов функции
        key_parts = [prefix]
        
        # Добавляем позиционные аргументы
        if args:
            for arg in args:
                key_parts.append(str(arg))
        
        # Добавляем именованные аргументы в отсортированном порядке
        if kwargs:
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}:{kwargs[k]}")
        
        # Объединяем все части ключа
        key_str = ":".join(key_parts)
        
        # Если ключ получился слишком длинным, хешируем его
        if len(key_str) > 100:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
            
        return key_str
    
    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis закрыто")

# Создаем глобальный экземпляр сервиса кэширования
cache_service = CacheService()

# Функции-обертки для обратной совместимости

async def initialize_redis() -> None:
    """Инициализация соединения с Redis"""
    await cache_service.initialize()

async def close_redis_connection() -> None:
    """Закрытие соединения с Redis"""
    await cache_service.close()

async def cache_get(key: str) -> Optional[Any]:
    """
    Получение данных из кэша по ключу
    
    Args:
        key: Ключ кэша
        
    Returns:
        Данные из кэша или None, если кэш не найден
    """
    return await cache_service.get(key)

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
    return await cache_service.set(key, data, ttl)

async def cache_delete(key: str) -> bool:
    """
    Удаление данных из кэша по ключу
    
    Args:
        key: Ключ кэша
        
    Returns:
        bool: True если данные успешно удалены, иначе False
    """
    return await cache_service.delete(key)

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удаление данных из кэша по шаблону ключа
    
    Args:
        pattern: Шаблон ключа
        
    Returns:
        bool: True если данные успешно удалены, иначе False
    """
    deleted = await cache_service.delete_pattern(pattern)
    return deleted > 0

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
        from sqlalchemy.ext.asyncio import AsyncSession
        from database import get_session
        
        # Используем новую сессию для получения данных отзыва
        session = await anext(get_session())
        review = await ReviewModel.get_by_id(session, review_id)
        
        # Удаляем кэш конкретного отзыва
        key = f"{CACHE_KEYS['review']}{review_id}"
        logger.debug(f"Инвалидация кэша отзыва {review_id}: {key}")
        await cache_service.delete(key)
        
        # Если отзыв относится к товару, инвалидируем соответствующие кэши для этого товара
        if review and review.product_id:
            product_id = review.product_id
            
            # Инвалидируем кэш статистики товара
            product_stats_key = f"{CACHE_KEYS['product_statistics']}{product_id}"
            logger.debug(f"Инвалидация кэша статистики товара {product_id}: {product_stats_key}")
            await cache_service.delete(product_stats_key)
            
            # Инвалидируем кэш отзывов для конкретного товара (все варианты страниц)
            product_reviews_pattern = f"{CACHE_KEYS['product_reviews']}{product_id}:*"
            logger.debug(f"Инвалидация кэша списков отзывов для товара {product_id} по шаблону {product_reviews_pattern}")
            await cache_service.delete_pattern(product_reviews_pattern)
            
            # Инвалидируем кэш статистики отзывов для конкретного товара
            review_stats_key = f"{CACHE_KEYS['product_review_stats']}{product_id}"
            logger.debug(f"Инвалидация кэша статистики отзывов товара {product_id}: {review_stats_key}")
            await cache_service.delete(review_stats_key)
            
            # Инвалидируем пакетные кэши, которые включают данный товар
            redis = cache_service.redis
            if redis:
                keys_to_check = await redis.keys(f"{CACHE_KEYS['product_batch_statistics']}*")
                product_id_str = str(product_id)
                
                for key in keys_to_check:
                    # Проверяем, содержит ли ключ ID товара
                    if product_id_str in key:
                        logger.debug(f"Инвалидация кэша пакетной статистики с ключом {key}")
                        await cache_service.delete(key)
        
        # Если это отзыв о магазине, инвалидируем кэш статистики магазина и отзывов
        if review and review.review_type == 'store':
            # Инвалидируем статистику магазина
            store_stats_key = f"{CACHE_KEYS['store_statistics']}stats"
            logger.debug(f"Инвалидация кэша статистики магазина: {store_stats_key}")
            await cache_service.delete(store_stats_key)
            
            # Инвалидируем кэши отзывов о магазине для конкретных страниц
            store_reviews_pattern = f"{CACHE_KEYS['store_reviews']}*"
            logger.debug(f"Инвалидация кэша отзывов магазина по шаблону: {store_reviews_pattern}")
            await cache_service.delete_pattern(store_reviews_pattern)
        
        # Если у отзыва есть автор, инвалидируем кэш отзывов пользователя
        if review and review.user_id:
            user_id = review.user_id
            user_reviews_pattern = f"{CACHE_KEYS['user_reviews']}{user_id}:*"
            logger.debug(f"Инвалидация кэша отзывов пользователя {user_id} по шаблону: {user_reviews_pattern}")
            await cache_service.delete_pattern(user_reviews_pattern)
        
        logger.info(f"Кэш отзыва {review_id} и связанных данных успешно инвалидирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инвалидации кэша отзыва: {str(e)}")
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
        # Удаляем кэш списков отзывов для товара для всех вариантов запросов
        pattern = f"{CACHE_KEYS['product_reviews']}{product_id}:*"
        logger.debug(f"Инвалидация кэша отзывов для товара {product_id} по шаблону {pattern}")
        deleted_count = await cache_service.delete_pattern(pattern)
        
        # Инвалидируем статистику товара
        stats_key = f"{CACHE_KEYS['product_statistics']}{product_id}"
        logger.debug(f"Инвалидация кэша статистики товара {product_id}: {stats_key}")
        await cache_service.delete(stats_key)
        
        review_stats_key = f"{CACHE_KEYS['product_review_stats']}{product_id}"
        logger.debug(f"Инвалидация кэша статистики отзывов товара {product_id}: {review_stats_key}")
        await cache_service.delete(review_stats_key)
        
        # Инвалидируем все пакетные запросы, которые могут включать этот товар
        redis = cache_service.redis
        if redis:
            keys_to_check = await redis.keys(f"{CACHE_KEYS['product_batch_statistics']}*")
            product_id_str = str(product_id)
            
            for key in keys_to_check:
                # Проверяем, содержит ли ключ ID товара
                if product_id_str in key:
                    logger.debug(f"Инвалидация кэша пакетной статистики с ключом {key}")
                    await cache_service.delete(key)
        
        logger.info(f"Кэш отзывов для товара {product_id} и связанных пакетных запросов инвалидирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инвалидации кэша отзывов для товара: {str(e)}")
        return False

async def invalidate_store_reviews_cache() -> bool:
    """
    Инвалидация кэша отзывов для магазина
    
    Returns:
        bool: True если кэш успешно инвалидирован, иначе False
    """
    try:
        # Удаляем кэш списков отзывов для магазина
        pattern = f"{CACHE_KEYS['store_reviews']}*"
        logger.debug(f"Инвалидация кэша отзывов магазина по шаблону: {pattern}")
        deleted_keys = await cache_service.delete_pattern(pattern)
        
        # Инвалидируем статистику магазина
        stats_key = f"{CACHE_KEYS['store_statistics']}stats"
        logger.debug(f"Инвалидация кэша статистики магазина: {stats_key}")
        await cache_service.delete(stats_key)
        
        logger.info(f"Кэш отзывов для магазина инвалидирован, удалено шаблонов: {pattern}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инвалидации кэша отзывов для магазина: {str(e)}")
        return False

async def invalidate_user_reviews_cache(user_id: int) -> bool:
    """
    Инвалидация кэша отзывов для конкретного пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если кэш успешно инвалидирован, иначе False
    """
    # Удаляем кэш списков отзывов для пользователя
    await cache_service.delete_pattern(f"{CACHE_KEYS['user_reviews']}{user_id}:*")
    
    # Инвалидируем разрешения пользователя
    await cache_service.delete_pattern(f"{CACHE_KEYS['permissions']}{user_id}:*")
    
    logger.info(f"Кэш отзывов для пользователя {user_id} инвалидирован")
    return True

# Декоратор для кэширования
def cached(ttl: int, key_prefix: str = None, key_builder: Callable = None):
    """
    Декоратор для кэширования результатов асинхронных функций
    
    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс ключа кэша (по умолчанию имя функции)
        key_builder: Функция для построения ключа кэша (если нужна особая логика)
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cache_service.enabled or not cache_service.redis:
                # Если кэширование отключено, просто выполняем функцию
                return await func(*args, **kwargs)
                
            # Определяем ключ кэша
            if key_builder:
                # Если указан пользовательский построитель ключа
                cache_key = key_builder(*args, **kwargs)
            else:
                # По умолчанию используем имя функции как префикс
                func_prefix = key_prefix or func.__name__
                cache_key = cache_service.get_key_for_function(func_prefix, *args, **kwargs)
                
            # Пытаемся получить результат из кэша
            cached_result = await cache_service.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Получены данные из кэша для ключа: {cache_key}")
                return cached_result
                
            # Если в кэше нет, выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем результат в кэш
            if result is not None:
                await cache_service.set(cache_key, result, ttl)
                logger.debug(f"Сохранены данные в кэш для ключа: {cache_key}")
                
            return result
            
        return wrapper
    return decorator 