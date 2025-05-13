"""Роутер для интеграции с API Boxberry для получения пунктов выдачи заказов с кэшированием."""

import logging
import json
import hashlib
from typing import Union, Dict, List, Optional

from fastapi import APIRouter, HTTPException
import httpx
logger = logging.getLogger("boxberry_router")
from cache import get_cached_data, set_cached_data, get_cached_data_by_pattern
from config import settings


router = APIRouter(
    prefix="/boxberry",
    tags=["boxberry"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)

BOXBERRY_CACHE_TTL = 86400  # 24 часа для кэша городов и пунктов выдачи
BOXBERRY_API_URL = "https://api.boxberry.ru/json.php"
BOXBERRY_TOKEN = settings.BOXBERRY_TOKEN
COUNTRY_CODE = "643"  # Код России

def get_cache_key(method: str, params: Optional[Dict] = None) -> str:
    """Генерирует ключ для кэша на основе метода и параметров."""
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

@router.get("/cities")
async def get_cities(country_code: str = COUNTRY_CODE):
    """
    Получает список городов из Boxberry API и кэширует результат.
    """
    try:
        # Проверяем кэш
        cache_key = get_cache_key("ListCitiesFull", {"CountryCode": country_code})
        cached_data = await get_cached_data(cache_key)
        
        if cached_data:
            logger.info("Возвращаю данные о городах из кэша")
            return cached_data
        
        # Если данных нет в кэше, запрашиваем их у API
        params = {
            "token": BOXBERRY_TOKEN,
            "method": "ListCitiesFull",
            "CountryCode": country_code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(BOXBERRY_API_URL, params=params)
            
            if response.status_code == 200:
                cities_data = response.json()
                
                # Сохраняем в кэш
                await set_cached_data(cache_key, cities_data, BOXBERRY_CACHE_TTL)
                logger.info("Сохраняю данные о городах в кэш")
                
                return cities_data
            else:
                logger.error("Ошибка при получении списка городов: %s", response.text)
                raise HTTPException(status_code=response.status_code, 
                                   detail=f"Ошибка API Boxberry: {response.text}")
    
    except Exception as e:
        logger.exception("Ошибка при получении списка городов Boxberry: %s", str(e))
        raise HTTPException(status_code=500, 
                           detail=f"Ошибка при получении списка городов: {str(e)}")

@router.get("/find-city-code")
async def find_city_code(city_name: str, country_code: str = COUNTRY_CODE):
    """
    Находит код города Boxberry по его названию.
    Используется для связи DaData и Boxberry.
    """
    try:
        # Получаем данные о городах (из кэша или API)
        cache_key = get_cache_key("ListCitiesFull", {"CountryCode": country_code})
        cities_data = await get_cached_data(cache_key)
        
        if not cities_data:
            # Если данных нет в кэше, запрашиваем их
            cities_data = await get_cities(country_code)
        
        # Нормализуем название города для поиска
        city_name_lower = city_name.lower().strip()
        
        # Ищем город по названию
        for city in cities_data:
            if city.get("Name", "").lower() == city_name_lower:
                return {"city_code": city.get("Code"), "city_data": city}
            
            # Также проверяем поле UniqName, если совпадения по Name не найдено
            if "UniqName" in city and city.get("UniqName", "").lower().startswith(city_name_lower):
                return {"city_code": city.get("Code"), "city_data": city}
        
        # Если город не найден
        return {"city_code": None, "error": "Город не найден"}
    
    except Exception as e:
        logger.exception("Ошибка при поиске кода города: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске кода города: {str(e)}")

@router.get("/pickup-points")
async def get_pickup_points(city_code: str, country_code: str = COUNTRY_CODE):
    """
    Получает список пунктов выдачи заказов для указанного города.
    """
    try:
        # Проверяем кэш
        cache_key = get_cache_key("ListPoints", {
            "CountryCode": country_code,
            "CityCode": city_code,
            "prepaid": "1"
        })
        cached_data = await get_cached_data(cache_key)
        
        if cached_data:
            logger.info("Возвращаю данные о пунктах выдачи из кэша для города %s", city_code)
            return cached_data
        
        # Если данных нет в кэше, запрашиваем их у API
        params = {
            "token": BOXBERRY_TOKEN,
            "method": "ListPoints",
            "CountryCode": country_code,
            "CityCode": city_code,
            "prepaid": "1"  # Возвращать все ПВЗ
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(BOXBERRY_API_URL, params=params)
            
            if response.status_code == 200:
                points_data = response.json()
                
                # Обрабатываем данные - отбираем только нужные поля для фронтенда
                processed_points = []
                for point in points_data:
                    processed_points.append({
                        "Code": point.get("Code"),
                        "Name": point.get("Name"),
                        "Address": point.get("Address"),
                        "WorkShedule": point.get("WorkShedule"),
                        "DeliveryPeriod": point.get("DeliveryPeriod", "")
                    })
                
                result = {
                    "original_data": points_data,
                    "simplified_data": processed_points
                }
                
                # Сохраняем в кэш
                await set_cached_data(cache_key, result, BOXBERRY_CACHE_TTL)
                logger.info("Сохраняю данные о пунктах выдачи в кэш для города %s", city_code)
                
                return result
            else:
                logger.error("Ошибка при получении списка ПВЗ: %s", response.text)
                raise HTTPException(status_code=response.status_code, 
                                   detail=f"Ошибка API Boxberry: {response.text}")
    
    except Exception as e:
        logger.exception("Ошибка при получении списка ПВЗ Boxberry: %s", str(e))
        raise HTTPException(status_code=500, 
                           detail=f"Ошибка при получении списка ПВЗ: {str(e)}")
