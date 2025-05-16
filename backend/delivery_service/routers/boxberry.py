"""Роутер для интеграции с API Boxberry для получения пунктов выдачи заказов с кэшированием."""

import logging

from fastapi import APIRouter, HTTPException
import httpx
logger = logging.getLogger("boxberry_router")
from cache import get_cached_data, set_cached_data, get_boxberry_cache_key, calculate_dimensions
from config import settings
from schemas import  DeliveryCalculationResponse, CartDeliveryRequest

router = APIRouter(
    prefix="/boxberry",
    tags=["boxberry"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)

@router.get("/cities")
async def get_cities(country_code: str = settings.BOXBERRY_COUNTRY_RUSSIA_CODE):
    """
    Получает список городов из Boxberry API и кэширует результат.
    """
    try:
        # Проверяем кэш
        cache_key = get_boxberry_cache_key("ListCitiesFull", {"CountryCode": country_code})
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
        cache_key = get_boxberry_cache_key("ListCitiesFull", {"CountryCode": country_code})
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
        cache_key = get_boxberry_cache_key("ListPoints", {
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
        # Проверяем, выбрана ли курьерская доставка
        if cart_request.delivery_type == 'boxberry_courier':
            # Проверяем наличие почтового индекса для курьерской доставки
            if not cart_request.zip_code:
                raise HTTPException(
                    status_code=400,
                    detail="Для курьерской доставки необходимо указать почтовый индекс"
                )
            
            # Проверяем, есть ли город в списке городов с курьерской доставкой
            # Запрашиваем список городов с курьерской доставкой
            courier_cities_cache_key = get_boxberry_cache_key("CourierListCities")
            courier_cities = await get_cached_data(courier_cities_cache_key)
            
            if not courier_cities:
                # Если данных нет в кэше, запрашиваем их у API
                params = {
                    "token": settings.BOXBERRY_TOKEN,
                    "method": "CourierListCities"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(settings.BOXBERRY_API_URL, params=params)
                    
                    if response.status_code == 200:
                        courier_cities = response.json()
                        
                        # Сохраняем в кэш на 3 часа (10800 секунд)
                        await set_cached_data(courier_cities_cache_key, courier_cities, 10800)
                        logger.info("Сохраняю данные о городах с курьерской доставкой в кэш")
                    else:
                        logger.error("Ошибка при получении списка городов с курьерской доставкой: %s", response.text)
                        raise HTTPException(
                            status_code=response.status_code, 
                            detail=f"Ошибка API Boxberry при получении списка городов: {response.text}"
                        )
            
            # Проверяем, есть ли город в списке городов с курьерской доставкой
            city_name = cart_request.city_name if hasattr(cart_request, 'city_name') else None
            
            if city_name:
                city_name_lower = city_name.lower().strip()
                city_found = False
                
                for city in courier_cities:
                    if city.get("City", "").lower() == city_name_lower:
                        city_found = True
                        break
                
                if not city_found:
                    logger.warning(f"Город {city_name} не найден в списке городов с курьерской доставкой")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Курьерская доставка в город {city_name} невозможна"
                    )
            
            # Проверяем почтовый индекс через ZipCheck API
            params = {
                "token": settings.BOXBERRY_TOKEN,
                "method": "ZipCheck",
                "zip": cart_request.zip_code,
                "CountryCode": settings.BOXBERRY_COUNTRY_RUSSIA_CODE
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.BOXBERRY_API_URL, params=params)
                
                if response.status_code == 200:
                    zip_check_data = response.json()
                    
                    # Проверяем формат данных, API может вернуть объект или список
                    if isinstance(zip_check_data, list) and zip_check_data:
                        # Если вернулся список, берем первый элемент
                        zip_check_data = zip_check_data[0]
                    
                    # Проверяем, возможна ли курьерская доставка по указанному индексу
                    if not zip_check_data.get("ExpressDelivery", False):
                        logger.warning(f"Курьерская доставка по индексу {cart_request.zip_code} невозможна")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Курьерская доставка по индексу {cart_request.zip_code} невозможна"
                        )
                    
                    logger.info(f"Курьерская доставка по индексу {cart_request.zip_code} возможна")
                else:
                    logger.error("Ошибка при проверке почтового индекса: %s", response.text)
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=f"Ошибка API Boxberry при проверке почтового индекса: {response.text}"
                    )
        
        # Рассчитываем общую стоимость заказа
        total_price = sum(item.price * item.quantity for item in cart_request.items)
        
        # Рассчитываем оптимальные габариты с помощью функции из cache.py
        dimensions = calculate_dimensions(
            cart_request.items,
            package_multiplier=settings.PACKAGE_MULTIPLIER
        )
        
        # Проверяем ограничения
        is_pvz = cart_request.delivery_type == 'boxberry_pickup_point'
        max_side = settings.BOXBERRY_MAX_PVZ_SIDE_LENGTH if is_pvz else settings.BOXBERRY_MAX_SIDE_LENGTH
        
        if max(dimensions['height'], dimensions['width'], dimensions['depth']) > max_side:
            raise HTTPException(
                status_code=400,
                detail=f"Превышена максимальная длина стороны: {max_side} см"
            )
        
        if (dimensions['height'] + dimensions['width'] + dimensions['depth']) > settings.BOXBERRY_MAX_TOTAL_DIMENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Сумма габаритов превышает {settings.BOXBERRY_MAX_TOTAL_DIMENSIONS} см"
            )
        
        # Формируем параметры для Boxberry API
        params = {
            "token": settings.BOXBERRY_TOKEN,
            "method": "DeliveryCalculation",
            "OrderSum": total_price,
            "BoxSizes": [{
                "Weight": dimensions['weight'],
                "Height": dimensions['height'],
                "Width": dimensions['width'],
                "Depth": dimensions['depth']
            }]
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
