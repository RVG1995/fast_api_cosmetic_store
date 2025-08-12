"""Модуль для работы с кэшированием данных в Redis."""

from typing import Any, Optional, Dict, Union, List
import logging
import hashlib
# Импорты для функций выше
import json

import pickle
import redis.asyncio as redis

from config import settings, get_redis_url, get_cache_ttl

logger = logging.getLogger("order_cache")

# Настройки кэширования из конфигурации
DEFAULT_CACHE_TTL = settings.ORDER_CACHE_TTL
CACHE_ENABLED = settings.CACHE_ENABLED

class CacheKeys:
    """Константы для ключей кэша"""
    ORDER_PREFIX = "order:"  # Префикс для ключей заказов
    USER_ORDERS_PREFIX = "user_orders:"  # Префикс для ключей списков заказов пользователя
    ADMIN_ORDERS_PREFIX = "admin_orders:"  # Префикс для ключей списков заказов в админке
    ORDER_STATUSES = "order_statuses"  # Ключ для списка статусов заказов
    ORDER_STATISTICS = "order_statistics"  # Ключ для статистики заказов
    ORDER_REPORTS_PREFIX = "order_statistics:report:"  # Префикс для ключей отчетов заказов
    USER_STATISTICS_PREFIX = "user_statistics:"  # Префикс для ключей статистики пользователя
    PRODUCTS_INFO_PREFIX = "products_info:"  # Префикс для ключей информации о продуктах
    PROMO_CODES = "promo_codes"  # Ключ для списка промокодов
    PROMO_CODE_PREFIX = "promo_code:"  # Префикс для ключей промокодов

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
            # Получаем URL для Redis из конфигурации
            redis_url = get_redis_url()
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=False  # Не декодируем ответы для поддержки pickle
            )
            # Healthcheck соединения
            await self.redis.ping()
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", 
                       settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка подключения к Redis для кэширования: %s", str(e))
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
                return pickle.loads(data)
            return None
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при получении данных из кэша: %s", str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
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
            await self.redis.set(key, pickle.dumps(value), ex=ttl)
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при сохранении данных в кэш: %s", str(e))
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
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при удалении ключа из кэша: %s", str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "order:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        if not self.enabled or not self.redis:
            return 0
            
        try:
            deleted_keys = []
            async for key in self.redis.scan_iter(match=pattern):
                deleted_keys.append(key)
            
            if deleted_keys:
                await self.redis.delete(*deleted_keys)
                logger.info("Удалены ключи по шаблону %s: %s шт.", pattern, len(deleted_keys))
                return len(deleted_keys)
            return 0
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при удалении ключей по шаблону %s: %s", pattern, str(e))
            return 0
    
    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Получает список ключей, соответствующих шаблону
        
        Args:
            pattern: Шаблон ключей для поиска (например, "dadata:address:*")
            
        Returns:
            List[str]: Список найденных ключей
        """
        if not self.enabled or not self.redis:
            return []
            
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            return keys
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при получении ключей по шаблону %s: %s", pattern, str(e))
            return []
    
    def get_key_for_user(self, user_id: Union[int, str], action: str) -> str:
        """
        Формирует ключ кэша для пользовательских данных
        
        Args:
            user_id: ID пользователя
            action: Название действия/метода
            
        Returns:
            str: Ключ кэша
        """
        return f"user:{user_id}:{action}"
    
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
            sorted_kwargs = sorted(kwargs.items())
            for key, value in sorted_kwargs:
                key_parts.append(f"{key}={value}")
        
        # Создаем полный ключ
        full_key = ":".join(key_parts)
        
        # Если ключ слишком длинный, создаем хеш
        if len(full_key) > 250:
            return f"{prefix}:{hashlib.md5(full_key.encode()).hexdigest()}"
        
        return full_key
    
    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis закрыто")

# Создаем экземпляр сервиса кэширования
cache_service = CacheService()

# Функции-хелперы для работы с кэшем
async def get_cached_data(key: str) -> Optional[Any]:
    """Получает данные из кэша"""
    return await cache_service.get(key)

async def set_cached_data(key: str, data: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """Сохраняет данные в кэш"""
    return await cache_service.set(key, data, ttl)

async def get_cached_data_by_pattern(pattern: str) -> Dict[str, Any]:
    """
    Получает все данные из кэша по шаблону ключей
    
    Args:
        pattern: Шаблон ключей для поиска (например, "dadata:address:*")
        
    Returns:
        Dict[str, Any]: Словарь {ключ: значение} для всех найденных ключей
    """
    if not CACHE_ENABLED:
        return {}
        
    try:
        keys = await cache_service.get_keys_by_pattern(pattern)
        if not keys:
            return {}
            
        result = {}
        for key in keys:
            data = await get_cached_data(key)
            if data:
                # Преобразуем bytes в строку, если нужно
                str_key = key.decode('utf-8') if isinstance(key, bytes) else key
                result[str_key] = data
                
        return result
    except Exception as e:
        logger.error("Ошибка при получении данных по шаблону %s: %s", pattern, str(e))
        return {}

async def invalidate_cache(*patterns: str) -> None:
    """
    Инвалидирует кэш по указанным шаблонам
    
    Args:
        *patterns: Шаблоны ключей для инвалидации
    """
    if not patterns:
        return
        
    for pattern in patterns:
        if not pattern:
            continue
        
        logger.info("Инвалидация кэша по шаблону: %s", pattern)
        await cache_service.delete_pattern(pattern)

# Закрытие соединения с Redis
async def close_redis() -> None:
    """Закрывает соединение с Redis"""
    await cache_service.close()

# Функции для кэширования заказов
async def cache_order(order_id: int, order_data: Dict[str, Any], admin: bool = False, cache_key: Optional[str] = None) -> None:
    """
    Кэширует данные заказа
    
    Args:
        order_id: ID заказа
        order_data: Данные заказа для кэширования
        admin: Флаг для отличия административного и пользовательского кэша
        cache_key: Произвольный ключ кэша (если None, будет сгенерирован автоматически)
    """
    if not CACHE_ENABLED:
        return
        
    try:
        # Определяем ключ кэша
        key = cache_key or (f"{CacheKeys.ORDER_PREFIX}{order_id}" + ("_admin" if admin else ""))
        
        # Получаем TTL для заказа из конфигурации
        ttl = get_cache_ttl().get("order", DEFAULT_CACHE_TTL)
        
        # Кэшируем данные
        await set_cached_data(key, order_data, ttl)
    except Exception as e:
        logger.error("Ошибка при кэшировании заказа %s: %s", order_id, str(e))

async def get_cached_order(order_id, user_id=None, admin=False):
    """
    Получает данные заказа из кэша
    
    Args:
        order_id: ID заказа
        user_id: ID пользователя (опционально, для логирования)
        admin: Флаг для отличия административного и пользовательского кэша
        
    Returns:
        Optional[Dict[str, Any]]: Данные заказа или None, если не найдены в кэше
    """
    if not CACHE_ENABLED:
        return None
        
    try:
        # Определяем ключ кэша
        key = f"{CacheKeys.ORDER_PREFIX}{order_id}" + ("_admin" if admin else "")
        
        # Получаем данные из кэша
        data = await get_cached_data(key)
        
        if data:
            logger.info("Найдены кэшированные данные заказа %s%s", 
                      order_id, f" для пользователя {user_id}" if user_id else "")
        
        return data
    except Exception as e:
        logger.error("Ошибка при получении заказа %s из кэша: %s", order_id, str(e))
        return None

async def invalidate_order_cache(order_id: int) -> None:
    """
    Инвалидирует кэш для заказа по ID
    
    Args:
        order_id: ID заказа
    """
    if not CACHE_ENABLED:
        return
        
    try:
        # Инвалидируем кэш заказа (и админский и пользовательский)
        await invalidate_cache(
            f"{CacheKeys.ORDER_PREFIX}{order_id}*",  # Все варианты этого заказа
            f"{CacheKeys.USER_ORDERS_PREFIX}*",  # Все списки заказов пользователей
            f"{CacheKeys.ADMIN_ORDERS_PREFIX}*",  # Все списки заказов в админке
        )
    except Exception as e:
        logger.error("Ошибка при инвалидации кэша заказа %s: %s", order_id, str(e))

# Функции для кэширования списков заказов
async def cache_orders_list(filter_params: str, orders_data: Any) -> bool:
    """Кэширует список заказов в административной панели"""
    key = f"{CacheKeys.ADMIN_ORDERS_PREFIX}{filter_params}"
    ttl = get_cache_ttl().get("orders_list", DEFAULT_CACHE_TTL)
    return await set_cached_data(key, orders_data, ttl)

async def get_cached_orders_list(filter_params: str) -> Optional[Any]:
    """Получает список заказов из кэша административной панели"""
    key = f"{CacheKeys.ADMIN_ORDERS_PREFIX}{filter_params}"
    return await get_cached_data(key)

async def cache_user_orders(user_id: int, filter_params: str, orders_data: Any) -> bool:
    """Кэширует список заказов пользователя"""
    key = f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:{filter_params}"
    ttl = get_cache_ttl().get("orders_list", DEFAULT_CACHE_TTL)
    return await set_cached_data(key, orders_data, ttl)

async def get_cached_user_orders(user_id: int, filter_params: str) -> Optional[Any]:
    """Получает список заказов пользователя из кэша"""
    key = f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:{filter_params}"
    return await get_cached_data(key)

async def cache_order_statistics(statistics_data: Any, user_id: Optional[int] = None) -> bool:
    """Кэширует статистику заказов (общую или для конкретного пользователя)"""
    key = CacheKeys.ORDER_STATISTICS if user_id is None else f"{CacheKeys.USER_STATISTICS_PREFIX}{user_id}"
    ttl = get_cache_ttl().get("statistics" if user_id is None else "user_statistics", DEFAULT_CACHE_TTL)
    return await set_cached_data(key, statistics_data, ttl)

async def get_cached_order_statistics(user_id: Optional[int] = None) -> Optional[Any]:
    """Получает статистику заказов из кэша (общую или для конкретного пользователя)"""
    key = CacheKeys.ORDER_STATISTICS if user_id is None else f"{CacheKeys.USER_STATISTICS_PREFIX}{user_id}"
    return await get_cached_data(key)

async def invalidate_statistics_cache() -> None:
    """Инвалидирует кэш статистики заказов"""
    await invalidate_cache(
        CacheKeys.ORDER_STATISTICS, 
        f"{CacheKeys.USER_STATISTICS_PREFIX}*",
        f"{CacheKeys.ORDER_REPORTS_PREFIX}*"  # Инвалидация кэша отчетов
    )

async def cache_order_statuses(statuses_data: Any) -> bool:
    """Кэширует список статусов заказов"""
    ttl = get_cache_ttl().get("statistics", DEFAULT_CACHE_TTL)
    return await set_cached_data(CacheKeys.ORDER_STATUSES, statuses_data, ttl)

async def get_cached_order_statuses() -> Optional[Any]:
    """Получает список статусов заказов из кэша"""
    return await get_cached_data(CacheKeys.ORDER_STATUSES)

async def invalidate_order_statuses_cache() -> None:
    """Инвалидирует кэш списка статусов заказов"""
    await cache_service.delete(CacheKeys.ORDER_STATUSES)

async def invalidate_user_orders_cache(user_id: int) -> None:
    """Инвалидирует кэш списков заказов пользователя"""
    await invalidate_cache(f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:*")

async def invalidate_promo_code_cache(promo_code_id: int) -> None:
    """
    Инвалидирует кэш для промокода по ID
    
    Args:
        promo_code_id: ID промокода
    """
    if not CACHE_ENABLED:
        return
        
    try:
        # Инвалидируем кэш промокода и список всех промокодов
        await invalidate_cache(
            f"{CacheKeys.PROMO_CODE_PREFIX}{promo_code_id}*",  # Конкретный промокод
            f"{CacheKeys.PROMO_CODES}*",  # Список всех промокодов
        )
        
        # Инвалидируем также кэш проверок промокодов, содержащий этот ID
        # Это сложнее сделать по шаблону, поэтому лучше инвалидировать все проверки
        await invalidate_cache(f"{CacheKeys.PROMO_CODE_PREFIX}check:*")
    except Exception as e:
        logger.error("Ошибка при инвалидации кэша промокода %s: %s", promo_code_id, str(e))

async def cache_promo_code_check(email: str, phone: str, promo_code_id: int, result: bool) -> None:
    """
    Кэширует результат проверки промокода для пользователя
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя 
        promo_code_id: ID промокода
        result: Результат проверки (True/False)
    """
    if not email and not phone:
        return
        
    # Создаем хеш для идентификации пользователя
    user_hash = hashlib.md5(((email or '') + (phone or '')).encode('utf-8')).hexdigest()
    
    # Создаем ключ кэша
    key = f"{CacheKeys.PROMO_CODE_PREFIX}check:{promo_code_id}:{user_hash}"
    
    # Устанавливаем TTL для проверки промокода (обычно короткий, 5-10 минут)
    ttl = 600  # 10 минут
    
    await set_cached_data(key, result, ttl)

async def get_cached_promo_code_check(email: str, phone: str, promo_code_id: int) -> Optional[bool]:
    """
    Получает результат проверки промокода для пользователя из кэша
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
        
    Returns:
        Optional[bool]: Кэшированный результат проверки или None, если не найден
    """
    if not email and not phone:
        return None
        
    # Создаем хеш для идентификации пользователя
    user_hash = hashlib.md5(((email or '') + (phone or '')).encode('utf-8')).hexdigest()
    
    # Создаем ключ кэша
    key = f"{CacheKeys.PROMO_CODE_PREFIX}check:{promo_code_id}:{user_hash}"
    
    return await get_cached_data(key)

async def invalidate_reports_cache() -> None:
    """Инвалидирует кэш отчетов заказов"""
    await invalidate_cache(f"{CacheKeys.ORDER_REPORTS_PREFIX}*")

# Специфичные функции кэширования для разных сервисов

# Функции для Boxberry
def get_boxberry_cache_key(method: str, params: Optional[Dict] = None) -> str:
    """Генерирует ключ для кэша Boxberry на основе метода и параметров."""
    key_parts = [method]
    
    if params:
        # Сортируем параметры для стабильного ключа
        for key in sorted(params.keys()):
            if params[key]:
                key_parts.append(f"{key}={params[key]}")
    
    key_str = ":".join(key_parts)
    # Хешируем для создания короткого ключа
    hash_obj = hashlib.md5(key_str.encode('utf-8'))
    hash_key = hash_obj.hexdigest()
    
    return f"boxberry:{hash_key}"

def get_stable_hash_key(prefix: str, payload: Any) -> str:
    """Создает стабильный ключ-хеш из произвольного payload (dict/list), используя JSON с сортировкой ключей.

    Args:
        prefix: Префикс ключа (пространство имён)
        payload: Произвольные данные (dict/list/скаляр)

    Returns:
        str: Ключ вида "{prefix}:{md5}"
    """
    try:
        key_str = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError:
        key_str = str(payload)
    return f"{prefix}:{hashlib.md5(key_str.encode('utf-8')).hexdigest()}"


# Функции для DaData
def normalize_obj(obj):
    """Нормализует объект для кэширования (приводит к нижнему регистру и сортирует ключи)."""
    if isinstance(obj, str):
        return obj.strip().lower()
    if isinstance(obj, list):
        return [normalize_obj(i) for i in obj]
    if isinstance(obj, dict):
        # Для словаря с query нормализуем и само значение query
        if "query" in obj and isinstance(obj["query"], str):
            obj_copy = obj.copy()
            obj_copy["query"] = obj_copy["query"].strip().lower()
            return {k: normalize_obj(obj_copy[k]) for k in sorted(obj_copy)}
        return {k: normalize_obj(obj[k]) for k in sorted(obj)}
    return obj

def get_dadata_cache_key(obj_type, query):
    """Генерирует ключ для кэша DaData с учетом регистра."""
    if isinstance(query, dict) and "query" in query:
        # Для запросов в формате словаря нормализуем запрос
        query_dict = query.copy()
        query_dict["query"] = query_dict["query"].lower().strip()
        # Создаем строку JSON из словаря с отсортированными ключами
        key_str = json.dumps(query_dict, ensure_ascii=False, sort_keys=True)
    else:
        # Для строковых запросов приводим к нижнему регистру
        key_str = str(query).lower().strip()
    
    # Хешируем для создания короткого ключа
    hash_obj = hashlib.md5(key_str.encode('utf-8'))
    hash_key = hash_obj.hexdigest()
    
    return f"dadata:{obj_type}:{hash_key}"

def trim_dadata_query(query):
    """Обрезает запрос DaData, чтобы получить подзапрос для поиска в кэше."""
    if isinstance(query, dict) and "query" in query:
        return query.copy()
    
    if isinstance(query, str):
        if len(query) <= 3:
            return query.lower().strip()  # Маленькие запросы возвращаем как есть
        
        # Обрезаем запрос до последнего пробела
        query_lower = query.lower().strip()
        last_space = query_lower.rfind(" ")
        if last_space > 0:
            # Если есть пробел, возвращаем строку до последнего пробела
            return query_lower[:last_space]
        # Если пробела нет, возвращаем первые несколько символов
        return query_lower[:3]
            
    return query  # Если запрос не строка и не словарь, возвращаем как есть

async def smart_dadata_cache_lookup(obj_type, query):
    """
    Умный поиск в кэше DaData: проверяет не только точное совпадение, но и кеш от более коротких запросов.
    Для подсказок по адресам и ФИО имеет смысл использовать кэш от более короткого запроса.
    
    Args:
        obj_type: Тип объекта (address/fio)
        query: Запрос для поиска
        
    Returns:
        Данные из кэша или None, если ничего не найдено
    """
    # Нормализуем запрос перед поиском в кэше
    if isinstance(query, dict):
        # Для запросов в формате словаря (address)
        if "query" in query:
            original_query = query.get("query", "").lower().strip()
            
            # Сначала ищем точное совпадение, используя get_cache_key
            exact_key = get_dadata_cache_key(obj_type, query)
            cached = await get_cached_data(exact_key)
            
            if cached:
                # Если нашли точное совпадение, возвращаем его
                logger.info("Точное попадание в кэш %s для запроса: %s", obj_type, original_query)
                return cached
                
            # Если точного совпадения нет, ищем частичное
            pattern = f"dadata:{obj_type}:*"
            cached_keys = await get_cached_data_by_pattern(pattern)
            
            # Фильтруем полученные результаты
            if cached_keys:
                # Ищем подходящие подсказки для нашего запроса
                prefix = original_query.lower().strip()
                
                if len(prefix) >= 3:  # Проверяем только если префикс достаточно длинный
                    for key, value in cached_keys.items():
                        # Проверяем, содержит ли кэшированный результат подходящие подсказки
                        if value and isinstance(value, dict) and "suggestions" in value:
                            # Фильтруем подсказки
                            filtered_suggestions = []
                            for suggestion in value.get("suggestions", []):
                                if "value" in suggestion:
                                    cached_value = suggestion.get("value", "").lower()
                                    # Проверяем, соответствует ли подсказка текущему запросу
                                    if prefix in cached_value or cached_value.startswith(prefix):
                                        filtered_suggestions.append(suggestion)
                            
                            if filtered_suggestions:
                                # Создаем новый результат с отфильтрованными подсказками
                                filtered_result = value.copy()
                                filtered_result["suggestions"] = filtered_suggestions
                                logger.info("Частичное попадание в кэш %s для запроса: %s (найдено %d подсказок)", 
                                          obj_type, original_query, len(filtered_suggestions))
                                return filtered_result
                
                logger.info("Частичное попадание в кэш %s, но нет релевантных подсказок для запроса: %s", 
                          obj_type, original_query)
    
    else:
        # Для запросов в формате строки (fio)
        original_query = str(query).lower().strip()
        
        # Сначала ищем точное совпадение, используя get_cache_key
        exact_key = get_dadata_cache_key(obj_type, query)
        cached = await get_cached_data(exact_key)
        
        if cached:
            # Если нашли точное совпадение, возвращаем его
            logger.info("Точное попадание в кэш %s для запроса: %s", obj_type, original_query)
            return cached
            
        # Если точного совпадения нет, ищем в кэше по шаблону
        pattern = f"dadata:{obj_type}:*"
        cached_keys = await get_cached_data_by_pattern(pattern)
        
        # Фильтруем полученные результаты
        if cached_keys:
            # Ищем подходящие подсказки для нашего запроса
            prefix = original_query.lower().strip()
            
            if len(prefix) >= 3:  # Проверяем только если префикс достаточно длинный
                for key, value in cached_keys.items():
                    if value and isinstance(value, dict) and "suggestions" in value:
                        # Фильтруем подсказки
                        filtered_suggestions = []
                        for suggestion in value.get("suggestions", []):
                            if "value" in suggestion:
                                cached_value = suggestion.get("value", "").lower()
                                # Проверяем, соответствует ли подсказка текущему запросу
                                if prefix in cached_value or cached_value.startswith(prefix):
                                    filtered_suggestions.append(suggestion)
                        
                        if filtered_suggestions:
                            # Создаем новый результат с отфильтрованными подсказками
                            filtered_result = value.copy()
                            filtered_result["suggestions"] = filtered_suggestions
                            logger.info("Частичное попадание в кэш %s для запроса: %s (найдено %d подсказок)", 
                                      obj_type, original_query, len(filtered_suggestions))
                            return filtered_result
            
            logger.info("Частичное попадание в кэш %s, но нет релевантных подсказок для запроса: %s", 
                      obj_type, original_query)
    
    # Если ничего не нашли в кэше
    logger.info("Промах кэша подсказок %s, отправляю запрос к API", obj_type)
    return None

# Функции для расчета габаритов заказов
def calculate_dimensions(
    items: List,
    weight_field: str = 'weight',
    height_field: str = 'height',
    width_field: str = 'width',
    depth_field: str = 'depth',
    package_multiplier: float = 1.2,
) -> Dict[str, int]:
    """
    Рассчитывает оптимальные габариты упаковки для группы товаров.
    Учитывает количество товаров и их габариты.
    
    Args:
        items: Список товаров с полями quantity и габаритами
        weight_field: Название поля с весом
        height_field: Название поля с высотой
        width_field: Название поля с шириной
        depth_field: Название поля с глубиной
        package_multiplier: Коэффициент для учета упаковки
        
    Returns:
        Dict[str, int]: Словарь с оптимальными габаритами
    """
    def _get_value(item, field: str, default):
        if isinstance(item, dict):
            return item.get(field, default)
        return getattr(item, field, default)
    
    # Собираем все товары с учетом количества
    all_items: List[Dict[str, float]] = []
    for item in items:
        quantity = int(_get_value(item, 'quantity', 1) or 1)
        weight = float(_get_value(item, weight_field, 500) or 500)
        height = int(_get_value(item, height_field, 10) or 10)
        width = int(_get_value(item, width_field, 10) or 10)
        depth = int(_get_value(item, depth_field, 10) or 10)
        for _ in range(quantity):
            all_items.append({'weight': weight, 'height': height, 'width': width, 'depth': depth})
    
    # Сортируем товары по убыванию объема
    all_items.sort(key=lambda x: x['height'] * x['width'] * x['depth'], reverse=True)
    
    # Рассчитываем общий вес
    total_weight = int(sum(item['weight'] for item in all_items))
    
    if not all_items:
        return {
            'weight': 500,
            'height': 10,
            'width': 10,
            'depth': 10
        }
    
    # Если товар один, возвращаем его габариты с учетом упаковки
    if len(all_items) == 1:
        return {
            'weight': total_weight,
            'height': int(all_items[0]['height'] * package_multiplier),
            'width': int(all_items[0]['width'] * package_multiplier),
            'depth': int(all_items[0]['depth'] * package_multiplier)
        }
    
    # Для нескольких товаров используем алгоритм упаковки
    # 1. Находим максимальную сторону среди всех товаров
    max_side = max(
        max(item['height'] for item in all_items),
        max(item['width'] for item in all_items),
        max(item['depth'] for item in all_items)
    )
    
    # 2. Рассчитываем общий объем
    total_volume = sum(
        item['height'] * item['width'] * item['depth'] 
        for item in all_items
    )
    
    # 3. Добавляем коэффициент упаковки
    total_volume *= package_multiplier
    
    # 4. Рассчитываем оптимальные габариты
    # Берем кубический корень из объема и округляем вверх
    side = int(total_volume ** (1/3)) + 1
    
    # Проверяем, что ни одна сторона не меньше максимальной стороны товара с учетом упаковки
    side = max(side, int(max_side * package_multiplier))
    
    return {
        'weight': total_weight,
        'height': side,
        'width': side,
        'depth': side
    }
