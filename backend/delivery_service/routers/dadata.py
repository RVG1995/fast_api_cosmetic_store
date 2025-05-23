"""Роутер для интеграции с API DaData для подсказок адресов и ФИО с кэшированием."""

import logging
from typing import Union

from fastapi import APIRouter, HTTPException
import httpx
logger = logging.getLogger("dadata_router")
from cache import set_cached_data, get_dadata_cache_key, smart_dadata_cache_lookup
from config import settings

DADATA_CACHE_TTL = settings.DADATA_CACHE_TTL

router = APIRouter(
    prefix="/dadata",
    tags=["dadata"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)

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
        
        # Проверяем кэш по нормализованному запросу, используя функцию из cache.py
        cached_result = await smart_dadata_cache_lookup("address", query_dict)
        
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
                cache_key = get_dadata_cache_key("address", query_dict)
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
        
        # Проверяем кэш по нормализованному запросу, используя функцию из cache.py
        cached_result = await smart_dadata_cache_lookup("fio", query_dict)
        
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
                cache_key = get_dadata_cache_key("fio", query_dict)
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
