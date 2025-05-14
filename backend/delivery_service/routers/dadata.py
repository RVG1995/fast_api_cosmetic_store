"""Роутер для интеграции с API DaData для подсказок адресов и ФИО с кэшированием."""

import logging
import json
import hashlib
from typing import Union

from fastapi import APIRouter, HTTPException
import httpx
logger = logging.getLogger("dadata_router")
from cache import get_cached_data, set_cached_data, get_cached_data_by_pattern
from config import settings

DADATA_CACHE_TTL = settings.DADATA_CACHE_TTL

router = APIRouter(
    prefix="/dadata",
    tags=["dadata"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)


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

def get_cache_key(obj_type, query):
    """Генерирует ключ для кэша с учетом регистра."""
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

def trim_query(query):
    """Обрезает запрос, чтобы получить подзапрос для поиска в кэше."""
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

async def smart_cache_lookup(obj_type, query):
    """
    Умный поиск в кэше: проверяет не только точное совпадение, но и кеш от более коротких запросов.
    Для подсказок по адресам и ФИО имеет смысл использовать кеш от более короткого запроса.
    
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
            exact_key = get_cache_key(obj_type, query)
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
        exact_key = get_cache_key(obj_type, query)
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

@router.post("/address")
async def suggest_address(query: dict):
    """Получить подсказки адреса"""
    try:
        # Извлекаем строку запроса, если запрос передан в формате {query: "строка"}
        query_dict = query.copy()  # Копируем, чтобы не изменять входной параметр
        if isinstance(query, dict) and "query" in query:
            query_text = query.get("query", "").strip()
            # Приводим к нижнему регистру для поиска в кэше
            query_dict["query"] = query_text.lower().strip()
        else:
            # Если запрос передан как строка напрямую
            query_text = str(query).strip()
            # Нормализуем для кэша
            query_dict = {"query": query_text.lower().strip()}

        # Если запрос пустой, возвращаем пустой результат
        if not query_text:
            return {"suggestions": []}
        
        # Проверяем кэш по нормализованному запросу
        cached_result = await smart_cache_lookup("address", query_dict)
        
        # Проверяем количество результатов
        should_refresh = False
        if cached_result:
            # Проверяем количество подсказок в результате
            suggestions_count = len(cached_result.get("suggestions", []))
            
            # Запрос нужно обновить если:
            # 1. В кэше нет подходящих подсказок
            # 2. Принудительно запрошено обновление через force_cache
            should_refresh = (
                suggestions_count == 0 or 
                query_dict.get("force_cache", False)
            )
            
            if should_refresh:
                logger.info("Нет результатов или запрошено обновление кэша для: %s", query_text)
                cached_result = None
            else:
                # Если кэш свежий и в нем есть результаты, используем его
                if suggestions_count > 0:
                    logger.info("Возвращаю %d подсказок из кэша для запроса: %s", suggestions_count, query_text)
                    return cached_result
        
        # Кэша нет или в нем нет результатов
        # API DaData для подсказок адресов
        api_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
        
        # Заголовки запроса
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {settings.DADATA_TOKEN}"
        }
        
        # Отправляем запрос (с оригинальным запросом, не с нормализованным)
        request_data = query.copy() if isinstance(query, dict) else {"query": str(query)}
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=request_data, headers=headers)
            logger.info("HTTP Request: %s %s \"%s\"", 
                      response.request.method, response.request.url, 
                      response.http_version + " " + str(response.status_code))
            
            # Если запрос успешен
            if response.status_code == 200:
                result = response.json()
                
                # Сохраняем результат в кэш, но с нормализованным запросом
                cache_key = get_cache_key("address", query_dict)
                await set_cached_data(cache_key, result, DADATA_CACHE_TTL)
                logger.info("Сохраняю в кэш подсказки адресов, ключ=%s, ttl=%s", cache_key, DADATA_CACHE_TTL)
                
                return result
            else:
                # Если запрос завершился с ошибкой
                logger.error("Ошибка запроса к DaData API для адреса: %s, статус: %d", 
                           query_text, response.status_code)
                raise HTTPException(status_code=response.status_code, 
                                   detail=f"Ошибка запроса к DaData API: {response.text}")
    
    except Exception as e:
        logger.exception("Ошибка при получении подсказок адреса: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при получении подсказок адреса: {str(e)}")

@router.post("/fio")
async def suggest_fio(query: Union[str, dict]):
    """Получить подсказки ФИО"""
    try:
        # Извлекаем строку запроса в зависимости от формата
        if isinstance(query, dict) and "query" in query:
            query_text = query.get("query", "").strip()
            # Создаем нормализованный запрос для кэша
            query_dict = query.copy()
            query_dict["query"] = query_text.lower().strip()
        else:
            query_text = str(query).strip()
            # Нормализуем для кэша
            query_dict = {"query": query_text.lower().strip()}
            
        # Если запрос пустой, возвращаем пустой результат
        if not query_text:
            return {"suggestions": []}
        
        # Проверяем кэш по нормализованному запросу
        cached_result = await smart_cache_lookup("fio", query_dict)
        
        # Проверяем количество результатов
        should_refresh = False
        if cached_result:
            # Проверяем количество подсказок в результате
            suggestions_count = len(cached_result.get("suggestions", []))
            
            # Запрос нужно обновить если:
            # 1. В кэше нет подходящих подсказок
            # 2. Принудительно запрошено обновление
            force_refresh = False
            if isinstance(query, dict):
                force_refresh = query.get("force_cache", False)
                
            should_refresh = (
                suggestions_count == 0 or 
                force_refresh
            )
            
            if should_refresh:
                logger.info("Нет результатов или запрошено обновление кэша для: %s", query_text)
                cached_result = None
            else:
                # Если кэш свежий и в нем есть результаты, используем его
                if suggestions_count > 0:
                    logger.info("Возвращаю %d подсказок из кэша для запроса: %s", suggestions_count, query_text)
                    return cached_result
        
        # Кэша нет или нужно обновление
        # API DaData для подсказок ФИО
        api_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/fio"
        
        # Заголовки запроса
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {settings.DADATA_TOKEN}"
        }
        
        # Подготавливаем данные запроса (используем оригинальный запрос)
        request_data = query if isinstance(query, dict) else {"query": query_text}
        
        # Отправляем запрос
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=request_data, headers=headers)
            logger.info("HTTP Request: %s %s \"%s\"", 
                      response.request.method, response.request.url, 
                      response.http_version + " " + str(response.status_code))
            
            # Если запрос успешен
            if response.status_code == 200:
                result = response.json()
                
                # Сохраняем результат в кэш с нормализованным ключом
                cache_key = get_cache_key("fio", query_dict)
                await set_cached_data(cache_key, result, DADATA_CACHE_TTL)
                logger.info("Сохраняю в кэш подсказки ФИО, ключ=%s, ttl=%s", cache_key, DADATA_CACHE_TTL)
                
                return result
            else:
                # Если запрос завершился с ошибкой
                logger.error("Ошибка запроса к DaData API для ФИО: %s, статус: %d", 
                           query_text, response.status_code)
                raise HTTPException(status_code=response.status_code, 
                                   detail=f"Ошибка запроса к DaData API: {response.text}")
    
    except Exception as e:
        logger.exception("Ошибка при получении подсказок ФИО: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при получении подсказок ФИО: {str(e)}")
