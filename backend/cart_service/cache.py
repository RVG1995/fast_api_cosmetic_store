import os
import json
import logging
from redis import asyncio as aioredis
from typing import Optional, Dict, Any, List, Callable, TypeVar, Union
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pathlib

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_cache")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Загружаем переменные окружения
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    logger.info(f"Переменные окружения загружены из {env_file}")
elif parent_env_file.exists():
    load_dotenv(dotenv_path=parent_env_file)
    logger.info(f"Переменные окружения загружены из {parent_env_file}")

# URL соединения с Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Время жизни кэша
CACHE_TTL = {
    "cart": int(os.getenv("CART_CACHE_TTL", "60")),  # 60 секунд для корзины
    "cart_summary": int(os.getenv("CART_SUMMARY_CACHE_TTL", "30")),  # 30 секунд для сводки корзины
    "admin_carts": int(os.getenv("ADMIN_CARTS_CACHE_TTL", "30"))  # 30 секунд для списка корзин в админке
}

# Префиксы ключей кэша
CACHE_KEYS = {
    "cart_user": "cart:user:",  # Корзина пользователя - cart:user:{user_id}
    "cart_session": "cart:session:",  # Корзина сессии - cart:session:{session_id}
    "cart_summary_user": "cart:summary:user:",  # Сводка корзины пользователя
    "cart_summary_session": "cart:summary:session:",  # Сводка корзины сессии
    "admin_carts": "admin:carts:"  # Список корзин для администраторов с параметрами
}

# Одиночное подключение к Redis
_redis_client = None

# Собственный JSONEncoder для обработки даты и времени
class DateTimeEncoder(json.JSONEncoder):
    """Класс для сериализации объектов datetime в JSON"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def get_redis():
    """
    Получает или создает подключение к Redis
    
    Returns:
        Redis: Клиент Redis или None в случае ошибки
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            logger.info(f"Установлено подключение к Redis: {REDIS_URL}")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {str(e)}")
            _redis_client = None
    
    return _redis_client

async def close_redis():
    """Закрывает соединение с Redis"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Соединение с Redis закрыто")

async def cache_get(key: str) -> Optional[Any]:
    """
    Получает данные из кэша
    
    Args:
        key (str): Ключ кэша
        
    Returns:
        Optional[Any]: Данные из кэша или None, если данные не найдены
    """
    redis = await get_redis()
    if not redis:
        return None
    
    try:
        data = await redis.get(key)
        if data:
            logger.debug(f"Данные получены из кэша: {key}")
            
            # Функция десериализации строк ISO 8601 обратно в datetime объекты
            def datetime_parser(dct):
                for k, v in dct.items():
                    if isinstance(v, str):
                        try:
                            # Пытаемся распарсить строку в формате ISO 8601
                            if 'T' in v and ('+' in v or 'Z' in v or '-' in v[10:]):
                                dct[k] = datetime.fromisoformat(v.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(v, dict):
                        dct[k] = datetime_parser(v)
                return dct
            
            return datetime_parser(json.loads(data))
            
        return None
    except Exception as e:
        logger.warning(f"Ошибка при получении данных из кэша ({key}): {str(e)}")
        return None

async def cache_set(key: str, data: Any, ttl: int) -> bool:
    """
    Сохраняет данные в кэш
    
    Args:
        key (str): Ключ кэша
        data (Any): Данные для сохранения
        ttl (int): Время жизни кэша в секундах
        
    Returns:
        bool: True, если данные успешно сохранены, иначе False
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        await redis.setex(key, ttl, json.dumps(data, cls=DateTimeEncoder))
        logger.debug(f"Данные сохранены в кэш: {key} (TTL: {ttl}с)")
        return True
    except Exception as e:
        logger.warning(f"Ошибка при сохранении данных в кэш ({key}): {str(e)}")
        return False

async def cache_delete(key: str) -> bool:
    """
    Удаляет данные из кэша
    
    Args:
        key (str): Ключ кэша
        
    Returns:
        bool: True, если данные успешно удалены, иначе False
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        await redis.delete(key)
        logger.debug(f"Данные удалены из кэша: {key}")
        return True
    except Exception as e:
        logger.warning(f"Ошибка при удалении данных из кэша ({key}): {str(e)}")
        return False

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удаляет данные из кэша по шаблону ключа
    
    Args:
        pattern (str): Шаблон ключа (например, "cart:user:*")
        
    Returns:
        bool: True, если данные успешно удалены, иначе False
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.debug(f"Удалено {len(keys)} ключей по шаблону: {pattern}")
        return True
    except Exception as e:
        logger.warning(f"Ошибка при удалении данных из кэша по шаблону ({pattern}): {str(e)}")
        return False

# Функции инвалидации кэша

async def invalidate_user_cart_cache(user_id: int) -> None:
    """
    Инвалидирует кэш корзины пользователя
    
    Args:
        user_id (int): ID пользователя
    """
    logger.info(f"Инвалидация кэша корзины пользователя: {user_id}")
    # Удаляем кэш корзины
    await cache_delete(f"{CACHE_KEYS['cart_user']}{user_id}")
    # Удаляем кэш сводки корзины
    await cache_delete(f"{CACHE_KEYS['cart_summary_user']}{user_id}")
    # Удаляем кэш списка корзин в админке
    await cache_delete_pattern(f"{CACHE_KEYS['admin_carts']}*")

async def invalidate_session_cart_cache(session_id: str) -> None:
    """
    Инвалидирует кэш корзины сессии
    
    Args:
        session_id (str): ID сессии
    """
    logger.info(f"Инвалидация кэша корзины сессии: {session_id}")
    # Удаляем кэш корзины
    await cache_delete(f"{CACHE_KEYS['cart_session']}{session_id}")
    # Удаляем кэш сводки корзины
    await cache_delete(f"{CACHE_KEYS['cart_summary_session']}{session_id}")

async def invalidate_admin_carts_cache() -> None:
    """
    Инвалидирует кэш списка корзин в админке
    """
    logger.info("Инвалидация кэша списка корзин в админке")
    await cache_delete_pattern(f"{CACHE_KEYS['admin_carts']}*")

# Декоратор для кэширования

T = TypeVar("T")

def cached(
    key_prefix: str,
    ttl: int,
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Декоратор для кэширования результатов асинхронных функций
    
    Args:
        key_prefix (str): Префикс ключа кэша
        ttl (int): Время жизни кэша в секундах
        key_builder (Optional[Callable[..., str]]): Функция для построения ключа кэша
            принимает те же аргументы, что и декорируемая функция
            
    Returns:
        Callable: Декоратор
        
    Example:
        @cached(
            key_prefix="cart:user:",
            ttl=CACHE_TTL["cart"],
            key_builder=lambda user_id, **kwargs: f"{user_id}"
        )
        async def get_user_cart(user_id: int, db: AsyncSession) -> CartSchema:
            # ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Строим ключ кэша
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                # По умолчанию используем все аргументы функции как часть ключа
                key_parts = []
                for arg in args:
                    if hasattr(arg, "__dict__"):
                        # Для объектов используем строковое представление
                        key_parts.append(str(arg))
                    else:
                        key_parts.append(str(arg))
                
                for k, v in kwargs.items():
                    if k == "db" or k == "session":
                        # Пропускаем сессию базы данных
                        continue
                    if hasattr(v, "__dict__"):
                        # Для объектов используем строковое представление
                        key_parts.append(f"{k}:{str(v)}")
                    else:
                        key_parts.append(f"{k}:{str(v)}")
                
                key_suffix = ":".join(key_parts)
            
            cache_key = f"{key_prefix}{key_suffix}"
            
            # Проверяем кэш
            cached_data = await cache_get(cache_key)
            if cached_data is not None:
                logger.debug(f"Возвращены кэшированные данные для {func.__name__}: {cache_key}")
                return cached_data
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем результат в кэш
            if result is not None:
                try:
                    # Пытаемся сериализовать и сохранить в кэш
                    await cache_set(cache_key, result, ttl)
                    logger.debug(f"Результат функции {func.__name__} сохранен в кэш: {cache_key}")
                except Exception as e:
                    # В случае ошибки сериализации логируем и продолжаем без кеширования
                    logger.warning(f"Ошибка при кешировании результата {func.__name__}: {str(e)}")
            
            return result
        return wrapper
    return decorator 