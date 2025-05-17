"""Роутер для интеграции с API Boxberry для получения пунктов выдачи заказов с кэшированием."""

import logging
import re

from fastapi import APIRouter, HTTPException, Body, Depends
import httpx

# Импорты из локальных модулей
from auth import require_admin
from cache import get_cached_data, set_cached_data, get_boxberry_cache_key, calculate_dimensions
from config import settings
from schemas import DeliveryCalculationResponse, CartDeliveryRequest

# Настройка логирования
logger = logging.getLogger("boxberry_router")

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
                        logger.info(f"Город {city_name} найден в списке городов с курьерской доставкой")
                        break
                
                if not city_found:
                    logger.warning(f"Город {city_name} не найден в списке городов с курьерской доставкой")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Курьерская доставка в город {city_name} невозможна"
                    )
            
            # Проверяем почтовый индекс через ListZips API
            zips_cache_key = get_boxberry_cache_key("ListZips")
            zip_codes_data = await get_cached_data(zips_cache_key)
            
            if not zip_codes_data:
                # Если данных нет в кэше, запрашиваем их у API
                params = {
                    "token": settings.BOXBERRY_TOKEN,
                    "method": "ListZips"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(settings.BOXBERRY_API_URL, params=params)
                    
                    if response.status_code == 200:
                        zip_codes_data = response.json()
                        
                        # Сохраняем в кэш на 12 часов (43200 секунд)
                        await set_cached_data(zips_cache_key, zip_codes_data, 43200)
                        logger.info("Сохраняю данные о почтовых индексах для курьерской доставки в кэш")
                    else:
                        logger.error("Ошибка при получении списка почтовых индексов: %s", response.text)
                        raise HTTPException(
                            status_code=response.status_code, 
                            detail=f"Ошибка API Boxberry при получении списка почтовых индексов: {response.text}"
                        )
            
            # Проверяем наличие индекса в списке
            user_zip_code = cart_request.zip_code
            zip_found = False
            zip_info = None
            
            for zip_item in zip_codes_data:
                if zip_item.get("Zip") == user_zip_code:
                    zip_found = True
                    zip_info = zip_item
                    break
            
            if not zip_found:
                logger.warning(f"Почтовый индекс {user_zip_code} не найден в списке индексов с курьерской доставкой")
                raise HTTPException(
                    status_code=400,
                    detail=f"Курьерская доставка по индексу {user_zip_code} невозможна"
                )
            
            # Проверяем, возможна ли курьерская доставка по указанному индексу
            if not zip_info.get("ZoneExpressDelivery"):
                logger.warning(f"Курьерская доставка по индексу {user_zip_code} невозможна (ZoneExpressDelivery не указана)")
                raise HTTPException(
                    status_code=400,
                    detail=f"Курьерская доставка по индексу {user_zip_code} невозможна"
                )
            
            logger.info(f"Курьерская доставка по индексу {user_zip_code} возможна, город: {zip_info.get('City', 'не указан')}")
        
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

@router.post("/create-parcel", response_model=dict, dependencies=[Depends(require_admin)])
async def create_boxberry_parcel(
    order_data: dict = Body(...),
):
    """
    Создание или обновление заказа в системе Boxberry и получение трек-номера.
    Доступно только для администраторов.
    
    - **order_data**: Данные заказа для создания/обновления посылки в Boxberry
    - Для обновления существующей посылки необходимо передать параметр updateByTrack с трек-номером
    """
    try:
        is_update = False
        update_track = None
        
        # Проверяем, передан ли трек-номер для обновления
        if "updateByTrack" in order_data and order_data["updateByTrack"]:
            is_update = True
            update_track = order_data["updateByTrack"]
            logger.info(f"Запрос на обновление посылки Boxberry с трек-номером: {update_track}")
        else:
            logger.info(f"Запрос на создание посылки Boxberry для заказа: {order_data.get('order_number', 'N/A')}")
        
        # Формируем базовые параметры запроса
        parcel_data = {
            "token": settings.BOXBERRY_TOKEN,
            "method": "ParselCreate",
            "sdata": {
                "order_id": order_data.get("order_number"),
                "price": str(order_data.get("price", 0)),
                "payment_sum": str(order_data.get("payment_sum", 0)),
                "delivery_sum": str(order_data.get("delivery_cost", 0)),
                "vid": "1" if order_data.get("delivery_type") == "boxberry_pickup_point" else "2",  # 1 - до ПВЗ, 2 - КД
                "shop": {"name": order_data.get("boxberry_point_id")},  # Код пункта поступления
                "customer": {
                    "fio": order_data.get("full_name", ""),
                    "phone": order_data.get("phone", "").replace("+7", "").replace("8", "", 1),
                    "email": order_data.get("email", "")
                },
                "items": [],
                "weights": {
                    "weight": "1000",  # в граммах
                    "x": "20",         # длина в см
                    "y": "20",         # ширина в см
                    "z": "10"          # высота в см
                }
            }
        }
        
        # Добавляем товары из заказа
        if order_data.get("items"):
            for item in order_data.get("items", []):
                parcel_data["sdata"]["items"].append({
                    "id": str(item.get("product_id", "")),
                    "name": item.get("product_name", ""),
                    "UnitName": "шт.",
                    "price": str(item.get("product_price", 0)),
                    "quantity": str(item.get("quantity", 1))
                })
        
        # Устанавливаем габариты посылки, если они переданы
        if order_data.get("dimensions"):
            dims = order_data.get("dimensions")
            parcel_data["sdata"]["weights"].update({
                "weight": str(int(float(dims.get("weight", 500)))),  # переводим кг в граммы
                "x": str(int(dims.get("width", 20))),
                "y": str(int(dims.get("depth", 20))),
                "z": str(int(dims.get("height", 10)))
            })
            logger.info(f"Использованы переданные габариты: {dims}")
            
        # Если переданы weights напрямую, используем их
        elif order_data.get("weights"):
            weights = order_data.get("weights")
            parcel_data["sdata"]["weights"].update({
                "weight": str(weights.get("weight", 500)),  # вес в граммах
                "x": str(weights.get("x", 20)),
                "y": str(weights.get("y", 20)),
                "z": str(weights.get("z", 10))
            })
            logger.info(f"Использованы переданные weights: {weights}")
            
        # Если не переданы габариты, но есть товары, рассчитываем их
        elif order_data.get("items"):
            # Создаем список товаров для расчета габаритов
            cart_items = []
            for item in order_data.get("items", []):
                cart_items.append({
                    "product_id": item.get("product_id"),
                    "quantity": item.get("quantity", 1),
                    "height": item.get("height", 10),
                    "width": item.get("width", 10),
                    "depth": item.get("depth", 10),
                    "weight": item.get("weight", 500)
                })
                
            if cart_items:
                dimensions = calculate_dimensions(cart_items, package_multiplier=settings.PACKAGE_MULTIPLIER)
                parcel_data["sdata"]["weights"].update({
                    "weight": str(int(dimensions["weight"])),  # вес в граммах
                    "x": str(int(dimensions["width"])),        # ширина в см
                    "y": str(int(dimensions["depth"])),        # глубина в см
                    "z": str(int(dimensions["height"]))        # высота в см
                })
                logger.info(f"Рассчитаны габариты на основе товаров: {dimensions}")
        
        # Добавляем данные в зависимости от типа доставки
        if order_data.get("delivery_type") == "boxberry_pickup_point":
            # Доставка до ПВЗ
            if order_data.get("boxberry_point_id"):
                parcel_data["sdata"]["issue"] = "1"  # Выдать на ПВЗ
                # Код ПВЗ Boxberry записываем в name пункта выдачи
                parcel_data["sdata"]["shop"]["name"] = str(order_data.get("boxberry_point_id"))
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Не указан код пункта выдачи BoxBerry"
                )
                
        elif order_data.get("delivery_type") == "boxberry_courier":
            # Курьерская доставка
            # Проверяем наличие адреса
            if not order_data.get("delivery_address"):
                raise HTTPException(
                    status_code=400,
                    detail="Не указан адрес доставки"
                )
            
            # Обязательно устанавливаем issue=1 для выдачи на ПВЗ
            parcel_data["sdata"]["issue"] = "1"
            
            # Инициализируем kurdost с пустыми данными
            kurdost_data = {
                "index": "",
                "citi": "",
                "addressp": ""
            }
            
            # Берем данные для курьерской доставки из входного запроса
            # Сначала проверяем, есть ли готовая структура kurdost
            if order_data.get("kurdost"):
                logger.info(f"Используем готовую структуру kurdost из запроса: {order_data.get('kurdost')}")
                kurdost_data.update(order_data.get("kurdost"))
            
            # Если нет готовой структуры kurdost, но есть address_data, используем его
            elif order_data.get("address_data"):
                # Используем переданные разобранные данные адреса
                address_data = order_data.get("address_data", {})
                logger.info(f"Используем address_data из запроса: {address_data}")
                
                # Формируем данные для курьерской доставки
                kurdost_data.update({
                    "index": address_data.get("postal_code", ""),
                    "citi": address_data.get("city", address_data.get("settlement", "")),
                })
                
                # Формируем строку адреса для addressp
                address_parts = []
                
                # Улица и дом
                if address_data.get("street_with_type"):
                    address_parts.append(address_data.get("street_with_type"))
                elif address_data.get("street"):
                    address_parts.append(f"ул {address_data.get('street')}")
                
                # Дом
                house_info = ""
                if address_data.get("house"):
                    house_type = address_data.get("house_type_full", "дом")
                    house_info = f"{house_type} {address_data.get('house')}"
                    address_parts.append(house_info)
                
                # Корпус/блок
                if address_data.get("block"):
                    block_type = address_data.get("block_type", "корп")
                    address_parts.append(f"{block_type} {address_data.get('block')}")
                
                # Квартира
                if address_data.get("flat"):
                    flat_type = address_data.get("flat_type_full", "кв")
                    address_parts.append(f"{flat_type} {address_data.get('flat')}")
                
                # Формируем полный адрес
                full_address = ", ".join(address_parts)
                
                # Если удалось сформировать адрес, используем его
                if full_address:
                    kurdost_data["addressp"] = full_address
                else:
                    # Иначе используем исходный адрес
                    kurdost_data["addressp"] = order_data.get("delivery_address", "")
                
                logger.info(f"Сформирован адрес для курьерской доставки: {kurdost_data['addressp']}")
            
            # Если нет ни kurdost, ни address_data, используем обычные поля
            else:
                logger.info("Используем обычные поля для курьерской доставки")
                
                # Извлекаем почтовый индекс из адреса, если он там есть
                zip_code = order_data.get("zip_code", "")
                if not zip_code:
                    # Ищем почтовый индекс в адресе (6 цифр в ряд)
                    zip_match = re.search(r'\b(\d{6})\b', order_data.get("delivery_address", ""))
                    if zip_match:
                        zip_code = zip_match.group(1)
                        logger.info(f"Извлечен почтовый индекс из адреса: {zip_code}")
                
                # Определяем город из адреса, если он не передан отдельно
                city_name = order_data.get("city_name", "")
                if not city_name and order_data.get("delivery_address"):
                    # Предполагаем, что город указан в начале адреса до первой запятой
                    address_parts = order_data.get("delivery_address", "").split(',')
                    if address_parts:
                        # Удаляем "г" или "г." в начале, если есть
                        city_part = address_parts[0].strip()
                        city_name = re.sub(r'^г\.?\s+', '', city_part)
                        logger.info(f"Извлечен город из адреса: {city_name}")
                
                # Формируем адрес без города и индекса
                delivery_address = order_data.get("delivery_address", "")
                address_parts = delivery_address.split(',')
                if len(address_parts) > 1:
                    addressp = ','.join(address_parts[1:]).strip()
                else:
                    addressp = delivery_address
                
                logger.info(f"Адрес без города: {addressp}")
                
                kurdost_data = {
                    "index": zip_code,
                    "citi": city_name,
                    "addressp": addressp
                }
            
            # Добавляем информацию о курьерской доставке
            parcel_data["sdata"]["kurdost"] = kurdost_data
            
            # Логирование данных курьерской доставки для отладки
            logger.info(f"Итоговые данные kurdost: {kurdost_data}")
            
        else:
            raise HTTPException(
                status_code=400,
                detail="Неподдерживаемый тип доставки. Поддерживаются только boxberry_pickup_point и boxberry_courier"
            )
        
        # Добавляем трек-номер для обновления если он есть
        if is_update:
            parcel_data["sdata"]["updateByTrack"] = update_track
        
        # Выполняем запрос к API BoxBerry
        logger.info(f"Отправка запроса на создание посылки в BoxBerry: {parcel_data}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.BOXBERRY_API_URL,
                json=parcel_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Ответ от BoxBerry API: {result}")
                
                # Проверяем наличие ошибки в ответе
                if isinstance(result, dict) and result.get("err"):
                    error_message = result.get("err", "Неизвестная ошибка")
                    logger.error(f"Ошибка при {'обновлении' if is_update else 'создании'} посылки в BoxBerry: {error_message}")
                    raise HTTPException(status_code=400, detail=f"Ошибка BoxBerry API: {error_message}")
                
                # Проверяем наличие трек-номера
                track_number = None
                
                # Проверяем успешность результата и структуру ответа
                if isinstance(result, dict):
                    track_number = result.get("track")
                    logger.info(f"Получен трек-номер BoxBerry: {track_number}")
                    
                    # Если это обновление и в ответе нет трек-номера, используем исходный
                    if is_update and not track_number:
                        track_number = update_track
                        logger.info(f"Используем исходный трек-номер для обновленной посылки: {track_number}")
                    
                    # Возвращаем результат
                    return {
                        "success": True,
                        "track_number": track_number,
                        "label": result.get("label"),
                        "message": "Посылка успешно обновлена" if is_update else "Посылка успешно создана"
                    }
                else:
                    logger.warning(f"Неожиданный формат ответа от BoxBerry API: {result}")
                    raise HTTPException(
                        status_code=400,
                        detail="Неожиданный формат ответа от BoxBerry API"
                    )
            else:
                logger.error(f"Ошибка запроса к BoxBerry API: HTTP {response.status_code}, {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка запроса к BoxBerry API: {response.text}"
                )
                
    except Exception as e:
        logger.exception(f"Ошибка при {'обновлении' if 'updateByTrack' in order_data else 'создании'} посылки в BoxBerry: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при {'обновлении' if 'updateByTrack' in order_data else 'создании'} посылки в BoxBerry: {str(e)}"
        )
