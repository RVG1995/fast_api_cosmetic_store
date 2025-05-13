"""Роутер для интеграции с API DaData для подсказок адресов и ФИО с кэшированием."""

import os
import logging
import json
import hashlib
from typing import Union
import time

from fastapi import APIRouter, HTTPException
import httpx
logger = logging.getLogger("dadata_router")
DADATA_CACHE_TTL = int(os.getenv("DADATA_CACHE_TTL", "86400"))  # TTL сутки
from cache import get_cached_data, set_cached_data, get_cached_data_by_pattern
from config import settings

router = APIRouter(
    prefix="/dadata",
    tags=["dadata"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)

HEADERS = {
    "Authorization": f"Token {settings.DADATA_TOKEN}",
    "Content-Type": "application/json"
}

def normalize_obj(obj):
    """Нормализует объект для кэширования (приводит к нижнему регистру и сортирует ключи)."""
    if isinstance(obj, str):
        return obj.strip().lower()
    if isinstance(obj, list):
        return [normalize_obj(i) for i in obj]
    if isinstance(obj, dict):
        return {k: normalize_obj(obj[k]) for k in sorted(obj)}
    return obj

def generate_cache_key(obj_type, query):
    """Генерирует ключ кэша для запроса."""
    query_str = query if isinstance(query, str) else json.dumps(query, ensure_ascii=False, sort_keys=True)
    return f"dadata:{obj_type}:{hashlib.md5(query_str.encode('utf-8')).hexdigest()}"

def trim_query(query):
    """Удаляет последние символы из запроса до последнего пробела или до полного удаления."""
    if not query or len(query) <= 1:
        return None
    
    # Ищем последний пробел
    last_space = query.rfind(' ')
    if last_space > 0:
        # Если есть пробел, возвращаем строку до него
        return query[:last_space]
    # Если нет пробела, возвращаем строку без последнего символа
    return query[:-1]

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
    if isinstance(query, dict):
        # Для запросов в формате словаря (address)
        original_query = query.get("query", "")
        
        # Сначала ищем точное совпадение
        norm_query = normalize_obj(query)
        key_str = json.dumps(norm_query, ensure_ascii=False, sort_keys=True)
        exact_key = f"dadata:{obj_type}:{hashlib.md5(key_str.encode('utf-8')).hexdigest()}"
        
        cached = await get_cached_data(exact_key)
        if cached:
            logger.info("Точное попадание в кэш %s для запроса: %s", obj_type, original_query)
            return cached
        
        # Если точного совпадения нет, ищем кеш для более коротких запросов
        current_query = original_query
        
        while current_query:
            current_query = trim_query(current_query)
            if not current_query:
                break
                
            # Создаем модифицированный запрос с более коротким значением
            modified_query = query.copy()
            modified_query["query"] = current_query
            
            norm_mod_query = normalize_obj(modified_query)
            mod_key_str = json.dumps(norm_mod_query, ensure_ascii=False, sort_keys=True)
            mod_key = f"dadata:{obj_type}:{hashlib.md5(mod_key_str.encode('utf-8')).hexdigest()}"
            
            cached = await get_cached_data(mod_key)
            if cached:
                # Фильтруем результаты, чтобы они соответствовали текущему запросу
                filtered_suggestions = []
                query_lower = original_query.lower()
                
                # Проходим по всем подсказкам из кэша
                for suggestion in cached.get("suggestions", []):
                    # Проверяем, соответствует ли подсказка тому, что уже ввел пользователь
                    suggestion_value = suggestion.get("value", "").lower()
                    if query_lower in suggestion_value or suggestion_value.startswith(query_lower):
                        filtered_suggestions.append(suggestion)
                
                # Если есть отфильтрованные подсказки, возвращаем их
                if filtered_suggestions:
                    logger.info("Частичное попадание в кэш %s для запроса: %s (использован кеш для: %s, найдено %d подсказок)", 
                               obj_type, original_query, current_query, len(filtered_suggestions))
                    
                    # Создаем новый объект с только теми подсказками, которые соответствуют запросу
                    filtered_result = cached.copy()
                    filtered_result["suggestions"] = filtered_suggestions
                    return filtered_result
                else:
                    logger.info("Частичное попадание в кэш %s, но нет релевантных подсказок для запроса: %s", 
                               obj_type, original_query)
        
        # Если пошаговое уменьшение не привело к результату, 
        # попробуем найти по шаблону используя get_cached_data_by_pattern
        pattern = f"dadata:{obj_type}:*"
        cached_keys = await get_cached_data_by_pattern(pattern)
        
        if cached_keys:
            # Ищем ключи, содержащие начало строки запроса
            prefix = original_query.lower().strip()
            if len(prefix) >= 3:  # Проверяем только если префикс достаточно длинный
                for key, value in cached_keys.items():
                    # Проверяем, содержит ли кэшированный запрос наш префикс
                    if value and isinstance(value, dict) and "query" in str(value):
                        cached_query = ""
                        
                        # Фильтруем подсказки
                        filtered_suggestions = []
                        for suggestion in value.get("suggestions", []):
                            if "value" in suggestion:
                                cached_value = suggestion.get("value", "").lower()
                                # Проверяем, соответствует ли подсказка текущему запросу
                                if prefix in cached_value or cached_value.startswith(prefix):
                                    filtered_suggestions.append(suggestion)
                                    cached_query = cached_value
                        
                        if filtered_suggestions:
                            logger.info("Шаблонное совпадение в кэше %s для запроса: %s (найдено %d подсказок)", 
                                      obj_type, original_query, len(filtered_suggestions))
                            
                            # Создаем новый объект с только теми подсказками, которые соответствуют запросу
                            filtered_result = value.copy()
                            filtered_result["suggestions"] = filtered_suggestions
                            return filtered_result
    
    else:
        # Для строковых запросов (fio)
        original_query = query
        
        # Сначала ищем точное совпадение
        norm_query = normalize_obj(query)
        exact_key = f"dadata:{obj_type}:{hashlib.md5(norm_query.encode('utf-8')).hexdigest()}"
        
        cached = await get_cached_data(exact_key)
        if cached:
            logger.info("Точное попадание в кэш %s для запроса: %s", obj_type, original_query)
            return cached
        
        # Если точного совпадения нет, ищем кеш для более коротких запросов
        current_query = original_query
        
        while current_query:
            current_query = trim_query(current_query)
            if not current_query:
                break
                
            norm_current = normalize_obj(current_query)
            current_key = f"dadata:{obj_type}:{hashlib.md5(norm_current.encode('utf-8')).hexdigest()}"
            
            cached = await get_cached_data(current_key)
            if cached:
                # Фильтруем результаты, чтобы они соответствовали текущему запросу
                filtered_suggestions = []
                query_lower = original_query.lower()
                
                # Проходим по всем подсказкам из кэша
                for suggestion in cached.get("suggestions", []):
                    # Проверяем, соответствует ли подсказка тому, что уже ввел пользователь
                    suggestion_value = suggestion.get("value", "").lower()
                    if query_lower in suggestion_value or suggestion_value.startswith(query_lower):
                        filtered_suggestions.append(suggestion)
                
                # Если есть отфильтрованные подсказки, возвращаем их
                if filtered_suggestions:
                    logger.info("Частичное попадание в кэш %s для запроса: %s (использован кеш для: %s, найдено %d подсказок)", 
                               obj_type, original_query, current_query, len(filtered_suggestions))
                    
                    # Создаем новый объект с только теми подсказками, которые соответствуют запросу
                    filtered_result = cached.copy()
                    filtered_result["suggestions"] = filtered_suggestions
                    return filtered_result
                else:
                    logger.info("Частичное попадание в кэш %s, но нет релевантных подсказок для запроса: %s", 
                               obj_type, original_query)
        
        # Если пошаговое уменьшение не привело к результату, 
        # попробуем найти по шаблону используя get_cached_data_by_pattern
        pattern = f"dadata:{obj_type}:*"
        cached_keys = await get_cached_data_by_pattern(pattern)
        
        if cached_keys:
            # Ищем ключи, содержащие начало строки запроса
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
                            logger.info("Шаблонное совпадение в кэше %s для запроса: %s (найдено %d подсказок)", 
                                      obj_type, original_query, len(filtered_suggestions))
                            
                            # Создаем новый объект с только теми подсказками, которые соответствуют запросу
                            filtered_result = value.copy()
                            filtered_result["suggestions"] = filtered_suggestions
                            return filtered_result
    
    return None

@router.post("/address")
async def suggest_address(query: dict):
    """Получить подсказки адреса"""
    try:
        # Извлекаем строку запроса, если запрос передан в формате {query: "строка"}
        query_dict = query
        if isinstance(query, dict) and "query" in query:
            query_text = query.get("query", "")
        else:
            # Если запрос передан как строка напрямую
            query_text = str(query)
            query_dict = {"query": query_text}

        # Если запрос пустой, возвращаем пустой результат
        if not query_text:
            return {"suggestions": []}
        
        # Проверяем кэш
        cached_result = await smart_cache_lookup("address", query_dict)
        
        # Проверяем свежесть данных в кэше и количество результатов
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

        if not cached_result:
            # Кэша нет или он устарел, делаем запрос к API
            logger.info("Промах кэша подсказок адресов, отправляю запрос к API")
            
            dadata_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {settings.DADATA_TOKEN}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    dadata_url,
                    headers=headers,
                    json=query_dict,
                    timeout=5.0
                )
                
                logger.info("HTTP Request: %s %s \"%s %s \"", 
                          response.request.method, response.request.url, 
                          response.http_version, response.status_code)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Добавляем метку времени к результату
                    result["timestamp"] = int(time.time())
                    
                    # Сохраняем в кэш
                    query_norm = normalize_obj(query_dict)
                    key_str = json.dumps(query_norm, ensure_ascii=False, sort_keys=True)
                    cache_key = f"dadata:address:{hashlib.md5(key_str.encode('utf-8')).hexdigest()}"
                    
                    logger.info("Сохраняю в кэш подсказки адресов, ключ=%s, ttl=%s", cache_key, DADATA_CACHE_TTL)
                    await set_cached_data(cache_key, result, DADATA_CACHE_TTL)
                    
                    return result
                else:
                    logger.error("Ошибка при запросе к DaData API: %s", response.text)
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Ошибка при запросе к DaData API"
                    )
        else:
            # Возвращаем данные из кэша, они прошли проверку свежести выше
            return cached_result
            
    except Exception as e:
        logger.exception("Ошибка при получении подсказок адреса: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении подсказок адреса: {str(e)}"
        )

@router.post("/fio")
async def suggest_fio(query: Union[str, dict]):
    """Получить подсказки ФИО"""
    try:
        # Извлекаем строку запроса в зависимости от формата
        if isinstance(query, dict) and "query" in query:
            query_text = query.get("query", "")
        else:
            query_text = str(query)
            
        # Если запрос пустой, возвращаем пустой результат
        if not query_text:
            return {"suggestions": []}
        
        # Проверяем кэш
        cached_result = await smart_cache_lookup("fio", query_text)
        
        # Проверяем свежесть данных в кэше и количество результатов
        should_refresh = False
        if cached_result:
            # Проверяем количество подсказок в результате
            suggestions_count = len(cached_result.get("suggestions", []))
            
            # Запрос нужно обновить если:
            # 1. В кэше нет подходящих подсказок
            # 2. Принудительно запрошено обновление через force_cache
            should_refresh = (
                suggestions_count == 0 or 
                "force_cache" in query_text
            )
            
            if should_refresh:
                logger.info("Нет результатов или запрошено обновление кэша для ФИО: %s", query_text)
                cached_result = None
            else:
                # Если в кэше есть результаты, используем его
                if suggestions_count > 0:
                    logger.info("Возвращаю %d подсказок из кэша для ФИО: %s", suggestions_count, query_text)
                    return cached_result
                
        if not cached_result:
            # Кэша нет, делаем запрос к API
            logger.info("Промах кэша подсказок ФИО, отправляю запрос к API")
            
            dadata_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/fio"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {settings.DADATA_TOKEN}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    dadata_url,
                    headers=headers,
                    json={"query": query_text},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Добавляем метку времени к результату
                    result["timestamp"] = int(time.time())
                    
                    # Сохраняем в кэш
                    query_norm = normalize_obj(query_text)
                    cache_key = f"dadata:fio:{hashlib.md5(query_norm.encode('utf-8')).hexdigest()}"
                    
                    logger.info("Сохраняю в кэш подсказки ФИО, ключ=%s, ttl=%s", cache_key, DADATA_CACHE_TTL)
                    await set_cached_data(cache_key, result, DADATA_CACHE_TTL)
                    
                    return result
                else:
                    logger.error("Ошибка при запросе к DaData API: %s", response.text)
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Ошибка при запросе к DaData API"
                    )
        else:
            # Возвращаем данные из кэша, они прошли проверку свежести выше
            return cached_result
            
    except Exception as e:
        logger.exception("Ошибка при получении подсказок ФИО: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении подсказок ФИО: {str(e)}"
        )
