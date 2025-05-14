"""Роутер для интеграции с API Boxberry для получения пунктов выдачи заказов с кэшированием."""

import logging
import hashlib
from typing import Dict, Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException
import httpx
logger = logging.getLogger("boxberry_router")
from cache import get_cached_data, set_cached_data
from config import settings
from schemas import DeliveryCalculationRequest, DeliveryCalculationResponse, CartDeliveryRequest, CartItemModel

router = APIRouter(
    prefix="/boxberry",
    tags=["boxberry"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)


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
async def get_cities(country_code: str = settings.BOXBERRY_COUNTRY_RUSSIA_CODE):
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
            "token": settings.BOXBERRY_TOKEN,
            "method": "ListCitiesFull",
            "CountryCode": country_code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.BOXBERRY_API_URL, params=params)
            
            if response.status_code == 200:
                cities_data = response.json()
                
                # Сохраняем в кэш
                await set_cached_data(cache_key, cities_data, settings.BOXBERRY_CACHE_TTL)
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
async def find_city_code(city_name: str, country_code: str = settings.BOXBERRY_COUNTRY_RUSSIA_CODE):
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
async def get_pickup_points(city_code: str, country_code: str = settings.BOXBERRY_COUNTRY_RUSSIA_CODE):
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
            "token": settings.BOXBERRY_TOKEN,
            "method": "ListPoints",
            "CountryCode": country_code,
            "CityCode": city_code,
            "prepaid": "1"  # Возвращать все ПВЗ
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.BOXBERRY_API_URL, params=params)
            
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
                await set_cached_data(cache_key, result, settings.BOXBERRY_CACHE_TTL)
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

    
@router.post("/calculate-from-cart", response_model=DeliveryCalculationResponse)
async def calculate_delivery_from_cart(cart_request: CartDeliveryRequest):
    """
    Расчет стоимости доставки для корзины товаров.
    
    Принимает список товаров в корзине, рассчитывает общий вес и габариты,
    а затем вызывает API Boxberry для расчета стоимости доставки.
    
    Возвращает стоимость доставки и срок доставки.
    """
    try:
        # Рассчитываем общую стоимость заказа
        total_price = sum(item.price * item.quantity for item in cart_request.items)
        
        # Формируем запрос для расчета доставки напрямую к API Boxberry
        # Подготавливаем параметры API запроса
        params = {
            "token": settings.BOXBERRY_TOKEN,
            "method": "DeliveryCalculation",
            "OrderSum": total_price,
        }
        
        # Определяем тип доставки
        if cart_request.delivery_type == 'boxberry_pickup_point':
            params["DeliveryType"] = "1"  # Доставка до ПВЗ
        elif cart_request.delivery_type == 'boxberry_courier':
            params["DeliveryType"] = "2"  # Курьерская доставка
        
        # PaySum зависит от способа оплаты
        # Если оплата при получении, то PaySum = OrderSum
        # Если оплата на сайте, то PaySum = 0
        params["PaySum"] = total_price if cart_request.is_payment_on_delivery else 0
        
        # Рассчитываем общий вес и габариты всех товаров
        total_weight = 0
        max_height = 0
        max_width = 0
        max_depth = 0
        
        for item in cart_request.items:
            for _ in range(item.quantity):
                # Суммируем вес каждого товара
                item_weight = item.weight or 500  # Вес товара (граммы)
                total_weight += item_weight
                
                # Находим максимальные габариты
                item_height = item.height or 10  # Высота (см)
                item_width = item.width or 10   # Ширина (см)
                item_depth = item.depth or 10   # Глубина (см)
                
                max_height = max(max_height, item_height)
                max_width = max(max_width, item_width)
                max_depth = max(max_depth, item_depth)
        
        # Устанавливаем минимальные значения если ничего не рассчитано
        total_weight = max(total_weight, 500)  # Минимум 500г
        max_height = max(max_height, 10)       # Минимум 10см
        max_width = max(max_width, 10)         # Минимум 10см
        max_depth = max(max_depth, 10)         # Минимум 10см
        
        # Создаем массив BoxSizes с габаритами
        params["BoxSizes"] = [
            {
                "Weight": total_weight,
                "Height": max_height,
                "Width": max_width,
                "Depth": max_depth
            }
        ]
        
        # Добавляем код пункта выдачи или почтовый индекс
        if cart_request.pvz_code:
            params["TargetStop"] = cart_request.pvz_code  # Код пункта выдачи
            
            # Логируем информацию о параметрах доставки до ПВЗ
            logger.info(f"Расчет доставки до пункта выдачи BoxBerry. " 
                        f"Код ПВЗ: {cart_request.pvz_code}")
        
        if cart_request.zip_code:
            params["Zip"] = cart_request.zip_code
            logger.info(f"Добавлен почтовый индекс для курьерской доставки: {cart_request.zip_code}")
        
        # Выполняем запрос к API
        async with httpx.AsyncClient() as client:            
            # Логируем запрос для отладки
            logger.info(f"Запрос к Boxberry API (корзина): {params}")
            
            try:
                response = await client.post(
                    settings.BOXBERRY_API_URL, 
                    json=params,
                    timeout=10.0  # Устанавливаем таймаут запроса в 10 секунд
                )
                
                # Дополнительная информация о запросе для отладки
                logger.debug(f"URL запроса к Boxberry API: {response.request.url}")
                
                if response.status_code == 200:
                    try:
                        delivery_data = response.json()
                        logger.debug(f"Ответ Boxberry API: {delivery_data}")
                        
                        # Проверяем на наличие ошибки в ответе
                        if isinstance(delivery_data, dict) and delivery_data.get("error", False):
                            error_message = delivery_data.get("message", "Неизвестная ошибка")
                            logger.error(f"Ошибка Boxberry API: {error_message}")
                            raise HTTPException(status_code=400, detail=f"Ошибка Boxberry API: {error_message}")
                        
                        # Обрабатываем успешный ответ, результат находится в поле result.DeliveryCosts
                        if "result" in delivery_data and "DeliveryCosts" in delivery_data["result"] and delivery_data["result"]["DeliveryCosts"]:
                            # Берем первый вариант доставки
                            delivery_costs = delivery_data["result"]["DeliveryCosts"][0]
                            
                            # Форматируем ответ
                            result = {
                                "price": float(delivery_costs.get("TotalPrice", 0)),
                                "price_base": float(delivery_costs.get("PriceBase", 0)),
                                "price_service": float(delivery_costs.get("PriceService", 0)),
                                "delivery_period": int(delivery_costs.get("DeliveryPeriod", 0))
                            }
                            
                            # Логируем результат
                            logger.info(f"Получена стоимость доставки для корзины: {result}")
                            
                            return result
                        else:
                            logger.warning("Получен пустой результат расчета доставки для корзины")
                            logger.debug(f"Полный ответ API: {delivery_data}")
                            
                            # Если нет данных о доставке, возвращаем нулевые значения
                            result = {
                                "price": 0.0,
                                "price_base": 0.0,
                                "price_service": 0.0,
                                "delivery_period": 0
                            }
                            
                            return result
                    except ValueError as e:
                        logger.error(f"Ошибка парсинга JSON ответа от Boxberry API: {e}")
                        logger.debug(f"Тело ответа: {response.text[:1000]}")  # Логируем первые 1000 символов
                        raise HTTPException(status_code=500, detail=f"Ошибка обработки ответа Boxberry API: {str(e)}")
                else:
                    logger.error(f"Ошибка при расчете стоимости доставки: HTTP {response.status_code}, {response.text}")
                    raise HTTPException(status_code=response.status_code, 
                                      detail=f"Ошибка API Boxberry: HTTP {response.status_code}, {response.text}")
            
            except httpx.TimeoutException:
                logger.error("Превышено время ожидания ответа от Boxberry API")
                raise HTTPException(status_code=504, detail="Превышено время ожидания ответа от API Boxberry")
            
            except httpx.RequestError as e:
                logger.error(f"Ошибка сетевого соединения с Boxberry API: {str(e)}")
                raise HTTPException(status_code=503, detail=f"Ошибка соединения с API Boxberry: {str(e)}")
                
    except HTTPException:
        # Передаем HTTPException дальше
        raise
    
    except Exception as e:
        logger.exception("Ошибка при расчете стоимости доставки из корзины: %s", str(e))
        raise HTTPException(status_code=500, 
                           detail=f"Ошибка при расчете стоимости доставки из корзины: {str(e)}")

@router.post("/calculate", response_model=DeliveryCalculationResponse)
async def calculate_delivery(calculation_request: DeliveryCalculationRequest):
    """
    Расчет стоимости доставки с помощью API Boxberry.
    
    Принимает вес посылки, город отправления, город назначения, стоимость заказа
    и другие опциональные параметры для расчета стоимости доставки.
    
    Возвращает стоимость доставки и срок доставки.
    """
    try:
        # Формируем параметры запроса к API
        params = {
            "token": settings.BOXBERRY_TOKEN,
            "method": "DeliveryCalculation",
            "OrderSum": calculation_request.order_sum,
        }
        
        # Определяем тип доставки
        if calculation_request.delivery_type == 'boxberry_pickup_point':
            params["DeliveryType"] = "1"  # Доставка до ПВЗ
        elif calculation_request.delivery_type == 'boxberry_courier':
            params["DeliveryType"] = "2"  # Курьерская доставка
        
        # PaySum зависит от способа оплаты
        # Если оплата при получении, то PaySum = OrderSum
        # Если оплата на сайте, то PaySum = 0
        params["PaySum"] = calculation_request.order_sum if calculation_request.is_payment_on_delivery else 0
        
        # Используем значения из запроса или значения по умолчанию
        weight = calculation_request.weight or 500
        height = calculation_request.height or 10
        width = calculation_request.width or 10
        depth = calculation_request.depth or 10
        
        # Создаем массив BoxSizes с габаритами
        params["BoxSizes"] = [
            {
                "Weight": weight,
                "Height": height,
                "Width": width,
                "Depth": depth
            }
        ]
        
        # Добавляем опциональные параметры, если они указаны
        if calculation_request.pvz_code:
            params["TargetStop"] = calculation_request.pvz_code  # Код пункта выдачи
            
            # Логируем информацию о параметрах доставки до ПВЗ
            logger.info(f"Расчет доставки до пункта выдачи BoxBerry. " 
                        f"Код ПВЗ: {calculation_request.pvz_code}")
            
        if calculation_request.delivery_sum:
            params["DeliverySum"] = calculation_request.delivery_sum
            
        if calculation_request.zip_code:
            params["Zip"] = calculation_request.zip_code
            logger.info(f"Добавлен почтовый индекс для курьерской доставки: {calculation_request.zip_code}")
        
        # Выполняем запрос к API
        async with httpx.AsyncClient() as client:
            # Логируем запрос для отладки
            logger.info(f"Запрос к Boxberry API: {params}")
            
            try:
                response = await client.post(
                    settings.BOXBERRY_API_URL, 
                    json=params,
                    timeout=10.0  # Устанавливаем таймаут запроса в 10 секунд
                )
                
                # Дополнительная информация о запросе для отладки
                logger.debug(f"URL запроса к Boxberry API: {response.request.url}")
                
                if response.status_code == 200:
                    try:
                        delivery_data = response.json()
                        logger.debug(f"Ответ Boxberry API: {delivery_data}")
                        
                        # Проверяем на наличие ошибки в ответе
                        if isinstance(delivery_data, dict) and delivery_data.get("error", False):
                            error_message = delivery_data.get("message", "Неизвестная ошибка")
                            logger.error(f"Ошибка Boxberry API: {error_message}")
                            raise HTTPException(status_code=400, detail=f"Ошибка Boxberry API: {error_message}")
                        
                        # Обрабатываем успешный ответ, результат находится в поле result.DeliveryCosts
                        if "result" in delivery_data and "DeliveryCosts" in delivery_data["result"] and delivery_data["result"]["DeliveryCosts"]:
                            # Берем первый вариант доставки
                            delivery_costs = delivery_data["result"]["DeliveryCosts"][0]
                            
                            # Форматируем ответ
                            result = {
                                "price": float(delivery_costs.get("TotalPrice", 0)),
                                "price_base": float(delivery_costs.get("PriceBase", 0)),
                                "price_service": float(delivery_costs.get("PriceService", 0)),
                                "delivery_period": int(delivery_costs.get("DeliveryPeriod", 0))
                            }
                            
                            # Логируем результат
                            logger.info(f"Получена стоимость доставки: {result}")
                            
                            return result
                        else:
                            # Если нет данных о доставке, возвращаем пустые данные
                            logger.warning("Получен пустой результат расчета доставки")
                            logger.debug(f"Полный ответ API: {delivery_data}")
                            result = {
                                "price": 0.0,
                                "price_base": 0.0,
                                "price_service": 0.0,
                                "delivery_period": 0
                            }
                        
                            return result
                    except ValueError as e:
                        logger.error(f"Ошибка парсинга JSON ответа от Boxberry API: {e}")
                        logger.debug(f"Тело ответа: {response.text[:1000]}")  # Логируем первые 1000 символов
                        raise HTTPException(status_code=500, detail=f"Ошибка обработки ответа Boxberry API: {str(e)}")
                else:
                    logger.error(f"Ошибка при расчете стоимости доставки: HTTP {response.status_code}, {response.text}")
                    raise HTTPException(status_code=response.status_code, 
                                       detail=f"Ошибка API Boxberry: HTTP {response.status_code}, {response.text}")
            
            except httpx.TimeoutException:
                logger.error("Превышено время ожидания ответа от Boxberry API")
                raise HTTPException(status_code=504, detail="Превышено время ожидания ответа от API Boxberry")
            
            except httpx.RequestError as e:
                logger.error(f"Ошибка сетевого соединения с Boxberry API: {str(e)}")
                raise HTTPException(status_code=503, detail=f"Ошибка соединения с API Boxberry: {str(e)}")
    
    except HTTPException:
        # Передаем HTTPException дальше
        raise
    
    except Exception as e:
        logger.exception("Ошибка при расчете стоимости доставки: %s", str(e))
        raise HTTPException(status_code=500, 
                           detail=f"Ошибка при расчете стоимости доставки: {str(e)}")
