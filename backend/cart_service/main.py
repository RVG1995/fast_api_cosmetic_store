from fastapi import FastAPI, Depends, HTTPException, Response, Cookie, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
from models import CartModel, CartItemModel
from database import setup_database, get_session, engine
from auth import get_current_user, get_session_id, User, get_current_admin_user
from schema import (
    CartItemAddSchema, CartItemUpdateSchema, CartSchema, CartItemSchema,  
    CartResponseSchema, ProductInfoSchema, CartSummarySchema,
    CleanupResponseSchema, ShareCartRequestSchema, ShareCartResponseSchema,
    LoadSharedCartSchema, UserCartSchema, PaginatedUserCartsResponse, UserCartItemSchema
)
from product_api import ProductAPI
from typing import Optional, List, Dict, Any, Annotated, Union
import logging
import uuid
import os
from datetime import datetime, timedelta
import asyncio
import httpx
from cache import (
    get_redis, close_redis, cached, cache_get, cache_set, cache_delete, 
    invalidate_user_cart_cache, invalidate_session_cart_cache, invalidate_admin_carts_cache,
    CACHE_KEYS, CACHE_TTL
)
import json
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_service")

# Инициализация ProductAPI
product_api = ProductAPI()

# Максимальный размер корзины для хранения в куках (в байтах)
MAX_COOKIE_SIZE = 4000  # ~4KB - безопасный размер для большинства браузеров

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который должен выполниться при запуске приложения
    await setup_database()  # создание таблиц в базе данных
    
    # Инициализируем Redis для кеширования
    await get_redis()
    
    logger.info("Сервис корзин запущен")
    
    yield  # здесь приложение будет работать
    
    # Код для завершения работы приложения
    logger.info("Завершение работы сервиса корзин")
    
    # Закрытие соединения с Redis
    await product_api.close()
    await close_redis()
    
    # Закрытие соединений с базой данных
    await engine.dispose()
    
    logger.info("Все соединения закрыты")

app = FastAPI(lifespan=lifespan)

# Настройка CORS
origins = [
    "http://localhost:3000",  # адрес фронтенда
    "http://127.0.0.1:3000",  # альтернативный адрес локального фронтенда
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8002",
    "http://127.0.0.1:8002",
    # Добавьте здесь другие разрешенные источники, если необходимо
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,   # Важно для работы с куками
    allow_methods=["*"],      # Разрешаем все методы 
    allow_headers=["*"],      # Разрешаем все заголовки
    expose_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Credentials"],  # Явно разрешаем заголовки
    max_age=86400,            # Кеширование CORS на 24 часа
)

# Алиас для зависимости сессии БД
SessionDep = Annotated[AsyncSession, Depends(get_session)]

async def get_cart_with_items(
    session: AsyncSession,
    user: Optional[User] = None
) -> Optional[CartModel]:
    """
    Получает корзину пользователя вместе с элементами.
    Только для авторизованных пользователей.
    """
    if user:
        # Если пользователь авторизован, ищем по user_id
        cart = await CartModel.get_user_cart(session, user.id)
        return cart
    else:
        # Если пользователь не авторизован, возвращаем None
        return None

async def enrich_cart_with_product_data(cart: CartModel) -> CartSchema:
    """
    Обогащает данные корзины информацией о продуктах
    """
    try:
        if not cart:
            logger.warning("Попытка обогатить данными пустую корзину (cart=None)")
            return CartSchema(
                id=0,
                user_id=None,
                session_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                items=[],
                total_items=0,
                total_price=0
            )
    
        logger.info(f"Обогащение данными корзины ID={cart.id}")
        
        # Проверяем, что cart.items не None
        items = getattr(cart, 'items', None) or []
        
        if not items:
            logger.info(f"Корзина ID={cart.id} не содержит элементов")
        
        # Собираем ID всех продуктов в корзине
        product_ids = [item.product_id for item in items]
        
        if product_ids:
            logger.info(f"Собрано {len(product_ids)} ID продуктов: {product_ids}")
        
        # Получаем информацию о продуктах, только если есть элементы в корзине
        products_info = await product_api.get_products_info(product_ids) if product_ids else {}
        
        if products_info:
            logger.info(f"Получена информация о {len(products_info)} продуктах")
        
        # Используем только безопасные атрибуты без повторного обращения к БД
        try:
            cart_created_at = cart.created_at
        except Exception:
            cart_created_at = datetime.now()
            
        try:
            cart_updated_at = cart.updated_at
        except Exception:
            cart_updated_at = datetime.now()
        
        # Преобразуем корзину в схему
        cart_dict = {
            "id": cart.id,
            "user_id": cart.user_id,
            "session_id": cart.session_id,
            "created_at": cart_created_at,
            "updated_at": cart_updated_at,
            "items": [],
            "total_items": 0,
            "total_price": 0
        }
        
        # Добавляем информацию о товарах, если есть элементы
        for item in items:
            try:
                product_info = products_info.get(item.product_id)
                
                item_dict = {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "added_at": item.added_at,
                    "updated_at": item.updated_at,
                    "product": None
                }
                
                if product_info:
                    # Добавляем информацию о продукте
                    item_dict["product"] = {
                        "id": product_info["id"],
                        "name": product_info["name"],
                        "price": product_info["price"],
                        "image": product_info.get("image"),
                        "stock": product_info["stock"]
                    }
                    
                    # Обновляем общие показатели корзины
                    cart_dict["total_items"] += item.quantity
                    cart_dict["total_price"] += product_info["price"] * item.quantity
                else:
                    logger.warning(f"Не удалось получить информацию о продукте ID={item.product_id}")
                
                cart_dict["items"].append(item_dict)
            except Exception as e:
                # Если произошла ошибка при обработке одного товара, пропускаем его
                logger.error(f"Ошибка при обработке товара ID={item.product_id}: {str(e)}")
                continue
        
        logger.info(f"Корзина ID={cart.id} успешно обогащена данными: {len(cart_dict['items'])} товаров, всего {cart_dict['total_items']} шт., на сумму {cart_dict['total_price']} ₽")
        
        return CartSchema(**cart_dict)
    except Exception as e:
        logger.error(f"Критическая ошибка при обогащении данными корзины: {str(e)}")
        # В случае критической ошибки возвращаем пустую корзину вместо None
        return CartSchema(
            id=cart.id if cart else 0,
            user_id=cart.user_id if cart else None,
            session_id=cart.session_id if cart else None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            items=[],
            total_items=0,
            total_price=0
        )

async def serialize_cart_for_cookie(cart_data: dict) -> str:
    """
    Сериализует данные корзины для хранения в куках.
    Содержит только необходимые данные: список товаров и их количество.
    
    Args:
        cart_data (dict): Данные корзины
        
    Returns:
        str: Сериализованная строка для хранения в куках
    """
    try:
        # Создаем упрощенное представление корзины для куки
        cookie_data = {
            "items": [
                {
                    "product_id": item["product_id"],
                    "quantity": item["quantity"]
                }
                for item in cart_data.get("items", [])
            ],
            "updated_at": datetime.now().isoformat()
        }
        
        # Сериализуем в JSON и сжимаем
        serialized_data = json.dumps(cookie_data)
        
        # Проверяем размер
        if len(serialized_data.encode('utf-8')) > MAX_COOKIE_SIZE:
            logger.warning(f"Размер данных корзины превышает максимально допустимый для куки: {len(serialized_data)} байт")
            # Если размер слишком большой, возвращаем только первые N товаров, которые поместятся
            items = cookie_data["items"]
            for i in range(len(items), 0, -1):
                cookie_data["items"] = items[:i]
                cookie_data["truncated"] = True
                serialized_data = json.dumps(cookie_data)
                if len(serialized_data.encode('utf-8')) <= MAX_COOKIE_SIZE:
                    logger.info(f"Корзина усечена до {i} товаров для размещения в куки")
                    break
        
        return serialized_data
    except Exception as e:
        logger.error(f"Ошибка при сериализации корзины для куки: {str(e)}")
        return json.dumps({"items": [], "error": "Ошибка сериализации"})

async def deserialize_cart_from_cookie(cookie_value: str) -> dict:
    """
    Десериализует данные корзины из куки
    
    Args:
        cookie_value (str): Значение куки
        
    Returns:
        dict: Десериализованные данные корзины
    """
    try:
        if not cookie_value:
            return {"items": []}
        
        # Десериализуем JSON
        cookie_data = json.loads(cookie_value)
        
        # Проверяем наличие необходимых полей
        if not isinstance(cookie_data, dict) or "items" not in cookie_data:
            logger.warning("Некорректный формат данных корзины в куки")
            return {"items": []}
        
        # Проверяем корректность списка товаров
        items = []
        for item in cookie_data.get("items", []):
            if not isinstance(item, dict):
                continue
                
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            
            if not product_id or not quantity or not isinstance(product_id, int) or not isinstance(quantity, int) or quantity <= 0:
                continue
                
            items.append({
                "product_id": product_id,
                "quantity": quantity
            })
        
        return {"items": items}
        
    except json.JSONDecodeError:
        logger.warning("Не удалось десериализовать данные корзины из куки")
        return {"items": []}
    except Exception as e:
        logger.error(f"Ошибка при десериализации корзины из куки: {str(e)}")
        return {"items": []}

async def cookie_cart_to_schema(cookie_cart: dict) -> CartSchema:
    """
    Преобразует данные корзины из куки в CartSchema с полной информацией о продуктах
    
    Args:
        cookie_cart (dict): Десериализованные данные корзины из куки
        
    Returns:
        CartSchema: Полные данные корзины
    """
    try:
        items = cookie_cart.get("items", [])
        
        # Если корзина пуста
        if not items:
            return CartSchema(
                id=0,
                user_id=None,
                session_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                items=[],
                total_items=0,
                total_price=0
            )
        
        # Собираем ID всех продуктов в корзине
        product_ids = [item["product_id"] for item in items]
        
        # Получаем информацию о продуктах
        products_info = await product_api.get_products_info(product_ids) if product_ids else {}
        
        # Создаем элементы корзины
        cart_items = []
        total_items = 0
        total_price = 0
        
        for idx, item in enumerate(items):
            product_id = item["product_id"]
            quantity = item["quantity"]
            product_info = products_info.get(product_id)
            
            if not product_info:
                logger.warning(f"Не удалось получить информацию о продукте ID={product_id}")
                continue
            
            # Создаем объект ProductInfoSchema
            product_schema = ProductInfoSchema(
                id=product_info["id"],
                name=product_info["name"],
                price=product_info["price"],
                image=product_info.get("image"),
                stock=product_info["stock"]
            )
            
            # Добавляем элемент корзины (используем idx как временный ID)
            cart_items.append(CartItemSchema(
                id=idx,  # Используем индекс как ID для анонимной корзины
                product_id=product_id,
                quantity=quantity,
                added_at=datetime.now(),
                updated_at=datetime.now(),
                product=product_schema
            ))
            
            # Обновляем общие показатели корзины
            total_items += quantity
            total_price += product_info["price"] * quantity
        
        # Создаем CartSchema
        return CartSchema(
            id=0,
            user_id=None,
            session_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            items=cart_items,
            total_items=total_items,
            total_price=total_price
        )
        
    except Exception as e:
        logger.error(f"Ошибка при преобразовании корзины из куки в схему: {str(e)}")
        # В случае ошибки возвращаем пустую корзину
        return CartSchema(
            id=0,
            user_id=None,
            session_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            items=[],
            total_items=0,
            total_price=0
        )

@app.get("/", tags=["Статус"])
async def root():
    """
    Базовый эндпоинт для проверки работоспособности сервиса
    """
    return {"message": "Сервис корзины работает"}

@app.get("/cart", response_model=CartSchema, tags=["Корзина"])
async def get_cart(
    response: Response,
    user: Optional[User] = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Получает корзину пользователя или создает новую.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится только в куках.
    """
    logger.info(f"Запрос корзины: user={user.id if user else 'Anonymous'}")
    
    try:
        # Для авторизованных пользователей используем БД
        if user:
            # Проверяем кэш корзины
            cache_key = f"{CACHE_KEYS['cart_user']}{user.id}"
            cached_cart = await cache_get(cache_key)
            
            if cached_cart:
                logger.info(f"Корзина получена из кэша: {cache_key}")
                return CartSchema(**cached_cart)
            
            # Если данных в кэше нет, пытаемся найти существующую корзину
            cart = await get_cart_with_items(db, user)
            
            if not cart:
                # Создаем новую корзину для авторизованного пользователя
                logger.info(f"Создание новой корзины для пользователя: user_id={user.id}")
                new_cart = CartModel(user_id=user.id)
                db.add(new_cart)
                await db.commit()
                
                # Загружаем созданную корзину с явной загрузкой items (пустой список)
                query = select(CartModel).options(
                    selectinload(CartModel.items)
                ).filter(CartModel.user_id == user.id)
                    
                result = await db.execute(query)
                cart = result.scalars().first()
                
                logger.info(f"Новая корзина создана: id={cart.id if cart else 'unknown'}")
                
                # Если у пользователя есть анонимная корзина в куках, объединяем их
                if cart_cookie:
                    try:
                        # Десериализуем корзину из куки
                        cookie_cart = await deserialize_cart_from_cookie(cart_cookie)
                        cookie_items = cookie_cart.get("items", [])
                        
                        if cookie_items:
                            logger.info(f"Объединение корзины из куки с корзиной пользователя: {len(cookie_items)} товаров")
                            
                            # Добавляем каждый товар из cookie_cart в корзину пользователя
                            for item in cookie_items:
                                product_id = item["product_id"]
                                quantity = item["quantity"]
                                
                                # Проверяем, есть ли уже такой товар в корзине
                                existing_item = await CartItemModel.get_item_by_product(db, cart.id, product_id)
                                
                                if existing_item:
                                    # Увеличиваем количество
                                    existing_item.quantity += quantity
                                    existing_item.updated_at = datetime.now()
                                else:
                                    # Добавляем новый товар
                                    new_item = CartItemModel(
                                        cart_id=cart.id,
                                        product_id=product_id,
                                        quantity=quantity
                                    )
                                    db.add(new_item)
                            
                            await db.commit()
                            
                            # Перезагружаем корзину с обновленными товарами
                            query = select(CartModel).options(
                                selectinload(CartModel.items)
                            ).filter(CartModel.id == cart.id)
                            
                            result = await db.execute(query)
                            cart = result.scalars().first()
                            
                            # Удаляем куку с анонимной корзиной
                            response.delete_cookie(key="cart_data")
                            logger.info("Кука с анонимной корзиной удалена после объединения")
                    except Exception as e:
                        logger.error(f"Ошибка при объединении корзин: {str(e)}")
            
            # Обогащаем корзину данными о продуктах
            enriched_cart = await enrich_cart_with_product_data(cart)
            
            # Кэшируем результат
            if enriched_cart:
                await cache_set(cache_key, enriched_cart.model_dump(), CACHE_TTL["cart"])
                logger.info(f"Корзина сохранена в кэш: {cache_key}")
            
            logger.info(f"Корзина пользователя успешно получена: id={cart.id}, items={len(cart.items) if hasattr(cart, 'items') and cart.items else 0}")
            
            return enriched_cart
            
        # Для анонимных пользователей используем куки
        else:
            # Пытаемся получить корзину из куки
            if cart_cookie:
                logger.info("Получение корзины из куки для анонимного пользователя")
                cookie_cart = await deserialize_cart_from_cookie(cart_cookie)
                enriched_cart = await cookie_cart_to_schema(cookie_cart)
                
                # Обновляем куку с текущей корзиной
                serialized_cart = await serialize_cart_for_cookie(enriched_cart.model_dump())
                response.set_cookie(
                    key="cart_data",
                    value=serialized_cart,
                    httponly=True,
                    max_age=60*60*24*30,  # 30 дней
                    secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
                )
                
                return enriched_cart
            
            # Если куки нет, создаем пустую корзину
            logger.info("Создание новой пустой корзины для анонимного пользователя")
            empty_cart = CartSchema(
                id=0,
                user_id=None,
                session_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                items=[],
                total_items=0,
                total_price=0
            )
            
            # Устанавливаем куку с пустой корзиной
            serialized_cart = await serialize_cart_for_cookie(empty_cart.model_dump())
            response.set_cookie(
                key="cart_data",
                value=serialized_cart,
                httponly=True,
                max_age=60*60*24*30,  # 30 дней
                secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
            )
            
            return empty_cart
            
    except Exception as e:
        logger.error(f"Ошибка при получении корзины: {str(e)}")
        # В случае ошибки возвращаем пустую корзину
        return CartSchema(
            id=0,
            user_id=user.id if user else None,
            session_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            items=[],
            total_items=0,
            total_price=0
        )

@app.post("/cart/items", response_model=CartResponseSchema, tags=["Корзина"])
async def add_item_to_cart(
    item: CartItemAddSchema,
    response: Response,
    user: Optional[User] = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Добавляет товар в корзину.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info(f"Запрос добавления товара в корзину: product_id={item.product_id}, quantity={item.quantity}, user={user.id if user else 'Anonymous'}")
    
    # Проверяем наличие товара на складе
    stock_check = await product_api.check_product_stock(item.product_id, item.quantity)
    
    if not stock_check["success"]:
        logger.warning(f"Ошибка проверки наличия товара: product_id={item.product_id}, quantity={item.quantity}, error={stock_check.get('error')}")
        return {
            "success": False,
            "message": "Ошибка при добавлении товара в корзину",
            "error": stock_check["error"]
        }
    
    try:
        # Для авторизованных пользователей используем БД
        if user:
            # Ищем или создаем корзину
            cart = await get_cart_with_items(db, user)
            
            if not cart:
                # Создаем новую корзину
                logger.info(f"Создание новой корзины: user_id={user.id}")
                new_cart = CartModel(user_id=user.id)
                db.add(new_cart)
                await db.commit()
                
                # Загружаем созданную корзину с явной загрузкой items (пустой список)
                query = select(CartModel).options(
                    selectinload(CartModel.items)
                ).filter(CartModel.user_id == user.id)
                    
                result = await db.execute(query)
                cart = result.scalars().first()
                
                logger.info(f"Новая корзина создана: id={cart.id if cart else 'unknown'}")
            
            # Проверяем, есть ли уже такой товар в корзине
            existing_item = await CartItemModel.get_item_by_product(db, cart.id, item.product_id)
            
            if existing_item:
                # Увеличиваем количество
                logger.info(f"Обновление существующего товара в корзине: id={existing_item.id}, новое количество={existing_item.quantity + item.quantity}")
                existing_item.quantity += item.quantity
                existing_item.updated_at = datetime.now()
            else:
                # Добавляем новый товар
                logger.info(f"Добавление нового товара в корзину: product_id={item.product_id}, quantity={item.quantity}")
                new_item = CartItemModel(
                    cart_id=cart.id,
                    product_id=item.product_id,
                    quantity=item.quantity
                )
                db.add(new_item)
            
            # Обновляем timestamp корзины
            cart.updated_at = datetime.now()
            
            await db.commit()
            
            # Загружаем обновленную корзину
            query = select(CartModel).options(
                selectinload(CartModel.items)
            ).filter(CartModel.id == cart.id)
            
            result = await db.execute(query)
            updated_cart = result.scalars().first()
            
            if not updated_cart:
                logger.error(f"Не удалось получить обновленную корзину после добавления товара")
                return {
                    "success": False,
                    "message": "Ошибка при добавлении товара в корзину",
                    "error": "Не удалось получить обновленную корзину"
                }
            
            # Обогащаем корзину данными о продуктах
            enriched_cart = await enrich_cart_with_product_data(updated_cart)
            
            # Инвалидируем кэш корзины
            await invalidate_user_cart_cache(user.id)
            
            return {
                "success": True,
                "message": "Товар успешно добавлен в корзину",
                "cart": enriched_cart
            }
        
        # Для анонимных пользователей используем куки
        else:
            # Получаем текущую корзину из куки
            current_cart = {"items": []}
            if cart_cookie:
                current_cart = await deserialize_cart_from_cookie(cart_cookie)
            
            # Проверяем, есть ли уже такой товар в корзине
            found = False
            for cart_item in current_cart["items"]:
                if cart_item["product_id"] == item.product_id:
                    # Увеличиваем количество
                    cart_item["quantity"] += item.quantity
                    found = True
                    logger.info(f"Обновление существующего товара в корзине (куки): product_id={item.product_id}, новое количество={cart_item['quantity']}")
                    break
            
            # Если товар не найден, добавляем новый
            if not found:
                current_cart["items"].append({
                    "product_id": item.product_id,
                    "quantity": item.quantity
                })
                logger.info(f"Добавление нового товара в корзину (куки): product_id={item.product_id}, quantity={item.quantity}")
            
            # Преобразуем корзину в полный формат с информацией о продуктах
            enriched_cart = await cookie_cart_to_schema(current_cart)
            
            # Сериализуем и сохраняем в куки
            serialized_cart = await serialize_cart_for_cookie(enriched_cart.model_dump())
            response.set_cookie(
                key="cart_data",
                value=serialized_cart,
                httponly=True,
                max_age=60*60*24*30,  # 30 дней
                secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
            )
            
            return {
                "success": True,
                "message": "Товар успешно добавлен в корзину",
                "cart": enriched_cart
            }
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара в корзину: {str(e)}")
        return {
            "success": False,
            "message": "Ошибка при добавлении товара в корзину",
            "error": str(e)
        }

@app.put("/cart/items/{item_id}", response_model=CartResponseSchema, tags=["Корзина"])
async def update_cart_item(
    item_id: int,
    item_data: CartItemUpdateSchema,
    response: Response,
    user: Optional[User] = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Обновляет количество товара в корзине.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info(f"Запрос обновления количества товара: item_id={item_id}, quantity={item_data.quantity}, user={user.id if user else 'Anonymous'}")
    
    # Проверяем допустимость количества
    if item_data.quantity <= 0:
        return {
            "success": False,
            "message": "Количество товара должно быть больше нуля",
            "error": "Некорректное количество товара"
        }
    
    try:
        # Для авторизованных пользователей используем БД
        if user:
            # Получаем элемент корзины
            query = select(CartItemModel).join(CartModel).filter(
                CartItemModel.id == item_id,
                CartModel.user_id == user.id
            )
            
            result = await db.execute(query)
            cart_item = result.scalars().first()
            
            if not cart_item:
                logger.warning(f"Элемент корзины не найден: item_id={item_id}, user_id={user.id}")
                return {
                    "success": False,
                    "message": "Товар не найден в корзине",
                    "error": "Элемент корзины не найден"
                }
            
            # Проверяем доступность товара на складе
            stock_check = await product_api.check_product_stock(cart_item.product_id, item_data.quantity)
            
            if not stock_check["success"]:
                logger.warning(f"Недостаточно товара на складе: product_id={cart_item.product_id}, requested={item_data.quantity}, available={stock_check.get('available_stock')}")
                return {
                    "success": False,
                    "message": "Ошибка при обновлении количества товара",
                    "error": stock_check["error"]
                }
            
            # Обновляем количество товара
            cart_id = cart_item.cart_id  # Запоминаем ID корзины
            
            # Используем SQL-запрос вместо прямого присваивания, чтобы избежать проблем с greenlet
            update_item_stmt = (
                update(CartItemModel)
                .where(CartItemModel.id == item_id)
                .values(quantity=item_data.quantity, updated_at=datetime.now())
            )
            await db.execute(update_item_stmt)
            
            # Отдельно обновляем timestamp корзины
            update_cart_stmt = (
                update(CartModel)
                .where(CartModel.id == cart_id)
                .values(updated_at=datetime.now())
            )
            await db.execute(update_cart_stmt)
            
            # Фиксируем транзакцию
            await db.commit()
            
            # Получаем обновленную корзину
            cart = await get_cart_with_items(db, user)
            
            # Обогащаем данными о продуктах
            enriched_cart = await enrich_cart_with_product_data(cart)
            
            # Инвалидируем кэш корзины
            await invalidate_user_cart_cache(user.id)
            
            return {
                "success": True,
                "message": "Количество товара успешно обновлено",
                "cart": enriched_cart
            }
        # Для анонимных пользователей используем куки
        else:
            # Получаем текущую корзину из куки
            if not cart_cookie:
                logger.warning("Попытка обновить товар в несуществующей корзине (куки отсутствуют)")
                return {
                    "success": False,
                    "message": "Корзина не найдена",
                    "error": "Корзина не найдена"
                }
            
            current_cart = await deserialize_cart_from_cookie(cart_cookie)
            
            # Ищем товар в корзине по индексу (item_id используется как индекс для анонимных корзин)
            if item_id < 0 or item_id >= len(current_cart.get("items", [])):
                logger.warning(f"Элемент корзины с индексом {item_id} не найден в куки")
                return {
                    "success": False,
                    "message": "Товар не найден в корзине",
                    "error": "Элемент корзины не найден"
                }
            
            # Получаем товар по индексу
            cart_item = current_cart["items"][item_id]
            product_id = cart_item["product_id"]
            
            # Проверяем доступность товара на складе
            stock_check = await product_api.check_product_stock(product_id, item_data.quantity)
            
            if not stock_check["success"]:
                logger.warning(f"Недостаточно товара на складе: product_id={product_id}, requested={item_data.quantity}, available={stock_check.get('available_stock')}")
                return {
                    "success": False,
                    "message": "Ошибка при обновлении количества товара",
                    "error": stock_check["error"]
                }
            
            # Обновляем количество товара
            current_cart["items"][item_id]["quantity"] = item_data.quantity
            logger.info(f"Обновлено количество товара в корзине (куки): product_id={product_id}, quantity={item_data.quantity}")
            
            # Преобразуем корзину в полный формат с информацией о продуктах
            enriched_cart = await cookie_cart_to_schema(current_cart)
            
            # Сериализуем и сохраняем в куки
            serialized_cart = await serialize_cart_for_cookie(enriched_cart.model_dump())
            response.set_cookie(
                key="cart_data",
                value=serialized_cart,
                httponly=True,
                max_age=60*60*24*30,  # 30 дней
                secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
            )
            
            return {
                "success": True,
                "message": "Количество товара успешно обновлено",
                "cart": enriched_cart
            }
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении количества товара: {str(e)}")
        return {
            "success": False,
            "message": "Ошибка при обновлении количества товара",
            "error": str(e)
        }

@app.delete("/cart/items/{item_id}", response_model=CartResponseSchema, tags=["Корзина"])
async def remove_cart_item(
    item_id: int,
    response: Response,
    user: Optional[User] = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Удаляет товар из корзины.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info(f"Запрос удаления товара из корзины: item_id={item_id}, user={user.id if user else 'Anonymous'}")
    
    try:
        # Для авторизованных пользователей используем БД
        if user:
            # Получаем элемент корзины
            query = select(CartItemModel).join(CartModel).filter(
                CartItemModel.id == item_id,
                CartModel.user_id == user.id
            )
            
            result = await db.execute(query)
            cart_item = result.scalars().first()
            
            if not cart_item:
                logger.warning(f"Элемент корзины не найден: item_id={item_id}, user_id={user.id}")
                return {
                    "success": False,
                    "message": "Товар не найден в корзине",
                    "error": "Элемент корзины не найден"
                }
            
            # Запоминаем ID корзины для последующей загрузки
            cart_id = cart_item.cart_id
            
            # Удаляем элемент корзины
            await db.delete(cart_item)
            
            # Обновляем timestamp корзины
            query = select(CartModel).filter(CartModel.id == cart_id)
            result = await db.execute(query)
            cart = result.scalars().first()
            
            if cart:
                cart.updated_at = datetime.now()
            
            await db.commit()
            
            # Загружаем обновленную корзину
            cart = await get_cart_with_items(db, user)
            
            # Обогащаем данными о продуктах
            enriched_cart = await enrich_cart_with_product_data(cart)
            
            # Инвалидируем кэш корзины
            await invalidate_user_cart_cache(user.id)
            
            return {
                "success": True,
                "message": "Товар успешно удален из корзины",
                "cart": enriched_cart
            }
            
        # Для анонимных пользователей используем куки
        else:
            # Получаем текущую корзину из куки
            if not cart_cookie:
                logger.warning("Попытка удалить товар из несуществующей корзины (куки отсутствуют)")
                return {
                    "success": False,
                    "message": "Корзина не найдена",
                    "error": "Корзина не найдена"
                }
            
            current_cart = await deserialize_cart_from_cookie(cart_cookie)
            
            # Ищем товар в корзине по индексу
            if item_id < 0 or item_id >= len(current_cart.get("items", [])):
                logger.warning(f"Элемент корзины с индексом {item_id} не найден в куки")
                return {
                    "success": False,
                    "message": "Товар не найден в корзине",
                    "error": "Элемент корзины не найден"
                }
            
            # Удаляем товар по индексу
            removed_item = current_cart["items"].pop(item_id)
            logger.info(f"Удален товар из корзины (куки): product_id={removed_item['product_id']}")
            
            # Преобразуем корзину в полный формат с информацией о продуктах
            enriched_cart = await cookie_cart_to_schema(current_cart)
            
            # Сериализуем и сохраняем в куки
            serialized_cart = await serialize_cart_for_cookie(enriched_cart.model_dump())
            response.set_cookie(
                key="cart_data",
                value=serialized_cart,
                httponly=True,
                max_age=60*60*24*30,  # 30 дней
                secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
            )
            
            return {
                "success": True,
                "message": "Товар успешно удален из корзины",
                "cart": enriched_cart
            }
            
    except Exception as e:
        logger.error(f"Ошибка при удалении товара из корзины: {str(e)}")
        return {
            "success": False,
            "message": "Ошибка при удалении товара из корзины",
            "error": str(e)
        }

@app.get("/cart/summary", response_model=CartSummarySchema, tags=["Корзина"])
async def get_cart_summary(
    response: Response,
    user: Optional[User] = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Получает сводную информацию о корзине (количество товаров, общая сумма).
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info(f"Запрос сводной информации о корзине: user={user.id if user else 'Anonymous'}")
    
    try:
        # Для авторизованных пользователей используем БД и кэш
        if user:
            # Проверяем кэш
            cache_key = f"{CACHE_KEYS['cart_summary_user']}{user.id}"
            cached_summary = await cache_get(cache_key)
            if cached_summary:
                logger.info(f"Сводка корзины получена из кэша: {cache_key}")
                return CartSummarySchema(**cached_summary)
            
            # Если данных в кэше нет, получаем корзину из БД
            cart = await get_cart_with_items(db, user)
            
            if not cart or not cart.items:
                # Если корзина не найдена или пуста
                summary = CartSummarySchema(
                    total_items=0,
                    total_price=0
                )
                
                # Кэшируем результат
                await cache_set(cache_key, summary.model_dump(), CACHE_TTL["cart_summary"])
                    
                return summary
            
            # Обрабатываем существующую корзину
            # Собираем ID всех продуктов в корзине
            product_ids = [item.product_id for item in cart.items]
            
            # Получаем информацию о продуктах
            products_info = await product_api.get_products_info(product_ids) if product_ids else {}
            
            # Вычисляем общее количество товаров и сумму
            total_items = 0
            total_price = 0
            
            for item in cart.items:
                product_info = products_info.get(item.product_id)
                if product_info:
                    total_items += item.quantity
                    total_price += product_info["price"] * item.quantity
            
            # Формируем ответ
            summary = CartSummarySchema(
                total_items=total_items,
                total_price=total_price
            )
            
            # Кэшируем результат
            await cache_set(cache_key, summary.model_dump(), CACHE_TTL["cart_summary"])
            logger.info(f"Сводка корзины пользователя сохранена в кэш: {cache_key}")
            
            return summary
        
        # Для анонимных пользователей используем куки
        else:
            # Получаем корзину из куки
            if cart_cookie:
                cookie_cart = await deserialize_cart_from_cookie(cart_cookie)
                enriched_cart = await cookie_cart_to_schema(cookie_cart)
                
                # Возвращаем сводную информацию из обогащенной корзины
                return CartSummarySchema(
                    total_items=enriched_cart.total_items,
                    total_price=enriched_cart.total_price
                )
            
            # Если куки нет, возвращаем пустую сводку
            return CartSummarySchema(
                total_items=0,
                total_price=0
            )
    except Exception as e:
        logger.error(f"Ошибка при получении сводной информации о корзине: {str(e)}")
        # В случае ошибки возвращаем пустые данные
        return CartSummarySchema(
            total_items=0,
            total_price=0
        )

@app.delete("/cart", response_model=CartResponseSchema, tags=["Корзина"])
async def clear_cart(
    response: Response,
    user: Optional[User] = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Очищает корзину пользователя.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info(f"Запрос очистки корзины: user={user.id if user else 'Anonymous'}")
    
    try:
        # Для авторизованных пользователей используем БД
        if user:
            # Ищем корзину
            cart = await get_cart_with_items(db, user)
            
            if not cart:
                logger.warning(f"Корзина не найдена для пользователя: user_id={user.id}")
                return {
                    "success": False,
                    "message": "Корзина не найдена",
                    "error": "Корзина не найдена"
                }
            
            # Проверяем, что cart.items не None
            items = getattr(cart, 'items', None)
            
            # Удаляем все элементы, если они есть
            if items:
                for item in items:
                    await db.delete(item)
                
                # Принудительно обновляем timestamp корзины
                cart.updated_at = datetime.now()
                
                await db.commit()
            
            # После удаления всех элементов, нам нужно явно перезагрузить корзину
            # с пустым списком элементов
            query = select(CartModel).options(
                selectinload(CartModel.items)
            ).filter(CartModel.id == cart.id)
            
            result = await db.execute(query)
            cart = result.scalars().first()
            
            # Обогащаем данными о продуктах (пустая корзина)
            enriched_cart = await enrich_cart_with_product_data(cart)
            
            # Инвалидируем кэш корзины
            await invalidate_user_cart_cache(user.id)
            
            return {
                "success": True,
                "message": "Корзина успешно очищена",
                "cart": enriched_cart
            }
            
        # Для анонимных пользователей используем куки
        else:
            # Создаем пустую корзину
            empty_cart = CartSchema(
                id=0,
                user_id=None,
                session_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                items=[],
                total_items=0,
                total_price=0
            )
            
            # Сериализуем и сохраняем в куки
            serialized_cart = await serialize_cart_for_cookie(empty_cart.model_dump())
            response.set_cookie(
                key="cart_data",
                value=serialized_cart,
                httponly=True,
                max_age=60*60*24*30,  # 30 дней
                secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
            )
            
            logger.info("Корзина в куках успешно очищена")
            
            return {
                "success": True,
                "message": "Корзина успешно очищена",
                "cart": empty_cart
            }
            
    except Exception as e:
        logger.error(f"Ошибка при очистке корзины: {str(e)}")
        return {
            "success": False,
            "message": "Ошибка при очистке корзины",
            "error": str(e)
        }

@app.post("/cart/merge", response_model=CartResponseSchema, tags=["Корзина"])
async def merge_carts(
    response: Response,
    user: User = Depends(get_current_user),
    cart_cookie: Optional[str] = Cookie(None, alias="cart_data"),
    db: AsyncSession = Depends(get_session)
):
    """
    Объединяет корзину из куки с корзиной пользователя после авторизации
    """
    if not user:
        logger.warning("Попытка объединения корзин без авторизации")
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    logger.info(f"Запрос на объединение корзин: user_id={user.id}")
    
    # Проверяем наличие куки с корзиной
    if not cart_cookie:
        logger.info(f"Нет куки с корзиной для объединения")
        
        # Ищем корзину по user_id
        user_cart = await CartModel.get_user_cart(db, user.id)
        
        # Если нет корзины пользователя, создаем новую
        if not user_cart:
            # Создаем новую корзину для пользователя
            logger.info(f"Создание новой корзины для пользователя: user_id={user.id}")
            new_cart = CartModel(user_id=user.id)
            db.add(new_cart)
            await db.commit()
            
            # Загружаем созданную корзину с явной загрузкой items (пустой список)
            query = select(CartModel).options(
                selectinload(CartModel.items)
            ).filter(CartModel.user_id == user.id)
                
            result = await db.execute(query)
            user_cart = result.scalars().first()
            logger.info(f"Новая корзина создана для пользователя: id={user_cart.id}")
        
        enriched_cart = await enrich_cart_with_product_data(user_cart)
        
        return {
            "success": True,
            "message": "Корзина не требует объединения",
            "cart": enriched_cart
        }
    
    # Десериализуем корзину из куки
    cookie_cart = await deserialize_cart_from_cookie(cart_cookie)
    cookie_items = cookie_cart.get("items", [])
    
    if not cookie_items:
        logger.info("Корзина в куках пуста, объединение не требуется")
        
        # Ищем корзину по user_id
        user_cart = await CartModel.get_user_cart(db, user.id)
        
        # Если нет корзины пользователя, создаем новую
        if not user_cart:
            # Создаем новую корзину для пользователя
            logger.info(f"Создание новой корзины для пользователя: user_id={user.id}")
            new_cart = CartModel(user_id=user.id)
            db.add(new_cart)
            await db.commit()
            
            # Загружаем созданную корзину с явной загрузкой items (пустой список)
            query = select(CartModel).options(
                selectinload(CartModel.items)
            ).filter(CartModel.user_id == user.id)
                
            result = await db.execute(query)
            user_cart = result.scalars().first()
            logger.info(f"Новая корзина создана для пользователя: id={user_cart.id}")
        
        enriched_cart = await enrich_cart_with_product_data(user_cart)
        
        # Удаляем куку с анонимной корзиной
        response.delete_cookie(key="cart_data")
        
        return {
            "success": True,
            "message": "Корзина не требует объединения",
            "cart": enriched_cart
        }
    
    # Ищем корзину пользователя
    user_cart = await CartModel.get_user_cart(db, user.id)
    
    # Если у пользователя нет корзины, создаем новую и добавляем товары из куки
    if not user_cart:
        # Создаем новую корзину
        logger.info(f"Создание новой корзины для пользователя: user_id={user.id}")
        new_cart = CartModel(user_id=user.id)
        db.add(new_cart)
        await db.commit()
        
        # Загружаем созданную корзину с пустым списком товаров
        query = select(CartModel).options(
            selectinload(CartModel.items)
        ).filter(CartModel.user_id == user.id)
            
        result = await db.execute(query)
        user_cart = result.scalars().first()
        logger.info(f"Новая корзина создана для пользователя: id={user_cart.id}")
        
        # Добавляем товары из куки в корзину пользователя
        for item in cookie_items:
            new_item = CartItemModel(
                cart_id=user_cart.id,
                product_id=item["product_id"],
                quantity=item["quantity"]
            )
            db.add(new_item)
            logger.info(f"Добавлен товар из куки в новую корзину: product_id={item['product_id']}, quantity={item['quantity']}")
        
        await db.commit()
        
        # Получаем обновленную корзину с товарами
        query = select(CartModel).options(
            selectinload(CartModel.items)
        ).filter(CartModel.id == user_cart.id)
        
        result = await db.execute(query)
        updated_cart = result.scalars().first()
        
        enriched_cart = await enrich_cart_with_product_data(updated_cart)
        
        # Удаляем куку с анонимной корзиной
        response.delete_cookie(key="cart_data")
        logger.info("Куки с анонимной корзиной удалены после переноса")
        
        return {
            "success": True,
            "message": "Товары из анонимной корзины перенесены в корзину пользователя",
            "cart": enriched_cart
        }
    
    # Объединяем товары из куки с существующей корзиной пользователя
    logger.info(f"Объединение корзины из куки с корзиной пользователя: user_cart_id={user_cart.id}, товаров в куки: {len(cookie_items)}")
    
    updated_count = 0
    new_count = 0
    
    for item in cookie_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        
        # Проверяем, есть ли уже такой товар в корзине
        existing_item = await CartItemModel.get_item_by_product(db, user_cart.id, product_id)
        
        if existing_item:
            # Проверяем наличие на складе для суммарного количества
            total_quantity = existing_item.quantity + quantity
            stock_check = await product_api.check_product_stock(product_id, total_quantity)
            
            if stock_check["success"]:
                existing_item.quantity = total_quantity
                existing_item.updated_at = datetime.now()
                updated_count += 1
                logger.info(f"Обновлено количество товара: product_id={product_id}, новое количество={total_quantity}")
            else:
                # Если не хватает на складе, устанавливаем максимально доступное количество
                available_stock = stock_check.get("available_stock", existing_item.quantity)
                existing_item.quantity = available_stock
                existing_item.updated_at = datetime.now()
                updated_count += 1
                logger.info(f"Обновлено количество товара (ограничено наличием): product_id={product_id}, новое количество={available_stock}")
        else:
            # Создаем новый элемент в корзине пользователя
            new_item = CartItemModel(
                cart_id=user_cart.id,
                product_id=product_id,
                quantity=quantity
            )
            db.add(new_item)
            new_count += 1
            logger.info(f"Добавлен новый товар: product_id={product_id}, количество={quantity}")
    
    # Обновляем timestamp корзины
    user_cart.updated_at = datetime.now()
    await db.commit()
    
    # Получаем обновленную корзину
    query = select(CartModel).options(
        selectinload(CartModel.items)
    ).filter(CartModel.id == user_cart.id)
    
    result = await db.execute(query)
    updated_cart = result.scalars().first()
    
    # Обогащаем данными о продуктах
    enriched_cart = await enrich_cart_with_product_data(updated_cart)
    
    # Инвалидируем кэш корзины
    await invalidate_user_cart_cache(user.id)
    
    # Удаляем куку с анонимной корзиной
    response.delete_cookie(key="cart_data")
    logger.info("Куки с анонимной корзиной удалены после объединения")
    
    logger.info(f"Корзины успешно объединены: обновлено товаров - {updated_count}, добавлено новых - {new_count}")
    
    return {
        "success": True,
        "message": "Корзины успешно объединены",
        "cart": enriched_cart
    }

@app.post("/cart/cleanup", response_model=CleanupResponseSchema, tags=["Администрирование"])
async def cleanup_anonymous_carts(
    request: Request,
    days: int = 1, 
    current_user: Optional[User] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Очищает анонимные корзины, которые не обновлялись указанное количество дней
    """
    # Проверка, что пользователь авторизован и имеет права администратора
    if current_user and not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_super_admin', False):
        logger.warning(f"Пользователь {current_user.id} не имеет прав администратора")
        raise HTTPException(
            status_code=403,
            detail="Для выполнения этой операции требуются права администратора",
        )
    
    user_info = f"пользователем {current_user.id}" if current_user else "через сервисный ключ"
    logger.info(f"Запуск очистки анонимных корзин старше {days} дней {user_info}")
    
    try:
        # Определяем дату, после которой корзины считаются устаревшими
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Выбираем анонимные корзины (с session_id, но без user_id), 
        # которые не обновлялись более указанного времени
        query = select(CartModel).filter(
            CartModel.user_id == None,  # Только анонимные корзины
            CartModel.session_id != None,  # С указанным session_id
            CartModel.updated_at < cutoff_date  # Не обновлялись в указанный период
        )
        
        result = await db.execute(query)
        carts_to_delete = result.scalars().all()
        
        if not carts_to_delete:
            logger.info("Не найдено устаревших анонимных корзин для удаления")
            return {
                "success": True,
                "deleted_count": 0,
                "message": "Не найдено устаревших анонимных корзин для удаления"
            }
        
        deleted_count = 0
        for cart in carts_to_delete:
            logger.info(f"Удаление корзины ID {cart.id}, session_id: {cart.session_id}, последнее обновление: {cart.updated_at}")
            await db.delete(cart)
            deleted_count += 1
        
        await db.commit()
        logger.info(f"Удалено устаревших анонимных корзин: {deleted_count}")
        
        # Инвалидируем кэш админки
        await invalidate_admin_carts_cache()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Успешно удалено {deleted_count} устаревших анонимных корзин"
        }
    except Exception as e:
        logger.error(f"Ошибка при очистке анонимных корзин: {str(e)}")
        return {
            "success": False,
            "deleted_count": 0,
            "message": f"Ошибка при выполнении очистки: {str(e)}"
        }

async def get_user_info(user_id: int) -> Dict[str, Any]:
    """
    Получает информацию о пользователе из сервиса авторизации
    """
    try:
        auth_service_url = os.environ.get("AUTH_SERVICE_URL", "http://localhost:8000")
        service_key = os.environ.get("INTERNAL_SERVICE_KEY", "test")
        
        logger.info(f"Запрос информации о пользователе {user_id} по URL: {auth_service_url}/admin/users/{user_id}")
        
        headers = {
            "service-key": service_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{auth_service_url}/admin/users/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # Проверяем наличие полей first_name и last_name в ответе
                if "first_name" not in user_data or "last_name" not in user_data:
                    logger.warning(f"В ответе от сервиса авторизации отсутствуют поля first_name или last_name: {user_data}")
                return user_data
            
            logger.warning(f"Не удалось получить информацию о пользователе {user_id}: код {response.status_code}, ответ: {response.text}")
            return {}
    except Exception as e:
        logger.error(f"Ошибка при запросе информации о пользователе {user_id}: {str(e)}")
        return {}

@app.get("/admin/carts", response_model=PaginatedUserCartsResponse, tags=["Администрирование"])
async def get_user_carts(
    request: Request,
    page: int = Query(1, description="Номер страницы", ge=1),
    limit: int = Query(10, description="Количество записей на странице", ge=1, le=100),
    sort_by: str = Query("updated_at", description="Поле для сортировки", regex="^(id|user_id|created_at|updated_at|items_count|total_price)$"),
    sort_order: str = Query("desc", description="Порядок сортировки", regex="^(asc|desc)$"),
    user_id: Optional[int] = Query(None, description="Фильтр по ID пользователя"),
    filter: Optional[str] = Query(None, description="Фильтр (with_items/empty)"),
    search: Optional[str] = Query(None, description="Поисковый запрос по ID корзины"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Получает список всех корзин пользователей (для администраторов)
    """
    logger.info(f"Запрос списка корзин пользователей: page={page}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}, user_id={user_id}, filter={filter}")
    
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['admin_carts']}page:{page}:limit:{limit}:sort:{sort_by}:{sort_order}:user:{user_id}:filter:{filter}:search:{search}"
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.info(f"Список корзин получен из кэша: {cache_key}")
            return PaginatedUserCartsResponse(**cached_data)
        
        # Получаем корзины пользователей с пагинацией
        carts, total_count = await CartModel.get_user_carts(
            session=db, 
            page=page, 
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
            filter=filter,
            search=search
        )
        
        # Получаем информацию о товарах для всех корзин
        product_ids = []
        for cart in carts:
            for item in cart.items:
                product_ids.append(item.product_id)
        
        # Получаем информацию о продуктах
        products_info = await product_api.get_products_info(list(set(product_ids))) if product_ids else {}
        
        # Формируем ответ
        result_items = []
        for cart in carts:
            cart_total_items = 0
            cart_total_price = 0
            cart_items = []
            
            # Получаем информацию о пользователе
            user_info = await get_user_info(cart.user_id) if cart.user_id else {}
            first_name = user_info.get('first_name', '')
            last_name = user_info.get('last_name', '')
            user_name = f"{first_name} {last_name}".strip()
            
            for item in cart.items:
                # Получаем информацию о продукте
                product_info = products_info.get(item.product_id, {})
                
                # Создаем объект элемента корзины
                cart_item = UserCartItemSchema(
                    id=item.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    added_at=item.added_at,
                    updated_at=item.updated_at,
                    product_name=product_info.get("name", "Неизвестный товар"),
                    product_price=product_info.get("price", 0)
                )
                
                # Обновляем общие показатели
                cart_total_items += item.quantity
                if product_info.get("price"):
                    cart_total_price += product_info["price"] * item.quantity
                
                cart_items.append(cart_item)
            
            # Создаем объект корзины
            user_cart = UserCartSchema(
                id=cart.id,
                user_id=cart.user_id,
                user_name=user_name or f"Пользователь {cart.user_id}",
                created_at=cart.created_at,
                updated_at=cart.updated_at,
                items=cart_items,
                total_items=cart_total_items,
                total_price=cart_total_price
            )
            
            result_items.append(user_cart)
        
        # Дополнительная сортировка на уровне приложения, если требуется
        if sort_by == 'items_count':
            result_items.sort(key=lambda x: x.total_items, reverse=(sort_order == 'desc'))
        elif sort_by == 'total_price':
            result_items.sort(key=lambda x: x.total_price, reverse=(sort_order == 'desc'))
        
        # Рассчитываем общее количество страниц
        total_pages = (total_count + limit - 1) // limit  # Округление вверх
        
        # Формируем и возвращаем ответ
        result = PaginatedUserCartsResponse(
            items=result_items,
            total=total_count,
            page=page,
            limit=limit,
            pages=total_pages
        )
        
        # Кэшируем результат
        await cache_set(cache_key, result.model_dump(), CACHE_TTL["admin_carts"])
        logger.info(f"Список корзин сохранен в кэш: {cache_key}")
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка корзин: {str(e)}")
        return PaginatedUserCartsResponse(
            items=[],
            total=0,
            page=page,
            limit=limit,
            pages=1
        )

@app.get("/admin/carts/{cart_id}", response_model=UserCartSchema, tags=["Администрирование"])
async def get_user_cart_by_id(
    request: Request,
    cart_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Получает информацию о конкретной корзине пользователя (для администратора)
    """
    logger.info(f"Запрос информации о корзине ID={cart_id} администратором {current_user.id}")
    
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['admin_carts']}cart:{cart_id}"
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.info(f"Информация о корзине ID={cart_id} получена из кэша")
            return UserCartSchema(**cached_data)
        
        # Получаем корзину по ID с загрузкой элементов
        cart = await CartModel.get_by_id(db, cart_id)
        
        if not cart:
            logger.warning(f"Корзина с ID={cart_id} не найдена")
            raise HTTPException(status_code=404, detail="Корзина не найдена")
        
        # Получаем дополнительную информацию о пользователе
        user_info = None
        if cart.user_id:
            user_info = await get_user_info(cart.user_id)
        
        # Получаем информацию о товарах в корзине
        product_ids = [item.product_id for item in cart.items] if cart.items else []
        products_info = await product_api.get_products_info(product_ids) if product_ids else {}
        
        # Вычисляем общую стоимость и формируем список элементов
        total_price = 0
        cart_items = []
        
        for item in cart.items:
            product_info = products_info.get(item.product_id, {})
            price = product_info.get("price", 0) if product_info else 0
            item_total = price * item.quantity
            total_price += item_total
            
            cart_item = UserCartItemSchema(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                added_at=item.added_at,
                updated_at=item.updated_at,
                product_name=product_info.get("name", "Неизвестный товар") if product_info else "Неизвестный товар",
                product_price=price
            )
            cart_items.append(cart_item)
        
        # Формируем ответ
        result = UserCartSchema(
            id=cart.id,
            user_id=cart.user_id,
            user_email=user_info.get("email") if user_info else None,
            user_name=f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() if user_info else None,
            session_id=cart.session_id,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
            items=cart_items,
            total_items=len(cart_items),
            items_count=len(cart_items),
            total_price=total_price
        )
        
        # Кэшируем результат
        await cache_set(cache_key, result.model_dump(), CACHE_TTL["admin_carts"])
        logger.info(f"Информация о корзине ID={cart_id} сохранена в кэш")
        
        return result
        
    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о корзине ID={cart_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True) 