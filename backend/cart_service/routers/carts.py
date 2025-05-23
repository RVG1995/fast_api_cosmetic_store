"""
Роутер для корзины
"""

from typing import Optional, Annotated
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from models import CartModel, CartItemModel
from database import get_session, engine
from auth import get_current_user, User
from schema import (
    CartItemAddSchema, CartItemUpdateSchema, CartSchema,  
    CartResponseSchema, CartSummarySchema, CartMergeSchema
)
from product_api import ProductAPI
from cache import (cache_get, cache_set,invalidate_user_cart_cache,CACHE_KEYS, CACHE_TTL)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_service")


# Инициализация ProductAPI
product_api = ProductAPI()


# Создание роутера
router = APIRouter(
    prefix="/cart",
    tags=["cart"],
    responses={404: {"description": "Not found"}},
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
        logger.info("Обогащение данными корзины ID=%d", cart.id)
        
        # Проверяем, что cart.items не None
        items = getattr(cart, 'items', None) or []
        
        if not items:
            logger.info("Корзина ID=%d не содержит элементов", cart.id)
        
        # Собираем ID всех продуктов в корзине
        product_ids = [item.product_id for item in items]
        
        if product_ids:
            logger.info("Собрано %d ID продуктов: %s", len(product_ids), product_ids)
        
        # Получаем информацию о продуктах, только если есть элементы в корзине
        products_info = await product_api.get_products_info(product_ids) if product_ids else {}
        
        if products_info:
            logger.info("Получена информация о %d продуктах", len(products_info))
        
        # Используем только безопасные атрибуты без повторного обращения к БД
        try:
            cart_created_at = cart.created_at
        except AttributeError:
            cart_created_at = datetime.now()
            
        try:
            cart_updated_at = cart.updated_at
        except AttributeError:
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
                    logger.warning("Не удалось получить информацию о продукте ID=%d", item.product_id)
                
                cart_dict["items"].append(item_dict)
            except (KeyError, AttributeError, ValueError, TypeError) as e:
                # Если произошла ошибка при обработке одного товара, пропускаем его
                logger.error("Ошибка при обработке товара ID=%d: %s", item.product_id, str(e))
                continue
        
        logger.info("Корзина ID=%d успешно обогащена данными: %d товаров, всего %d шт., на сумму %d ₽", cart.id, len(cart_dict['items']), cart_dict['total_items'], cart_dict['total_price'])
        
        return CartSchema(**cart_dict)
    except (KeyError, AttributeError, ValueError, TypeError) as e:
        logger.error("Критическая ошибка при обогащении данными корзины: %s", str(e))
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

@router.get("", response_model=CartSchema, tags=["Корзина"])
async def get_cart(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Получает корзину пользователя или создает новую.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится только в куках.
    """
    logger.info("Запрос корзины: user=%d", user.id if user else 'Anonymous')
    
    try:
        # Для авторизованных пользователей используем БД и кэш
        if user:
            # Проверяем кэш корзины
            cache_key = f"{CACHE_KEYS['cart_user']}{user.id}"
            cached_cart = await cache_get(cache_key)
            if cached_cart:
                logger.info("Корзина получена из кэша: %s", cache_key)
                return CartSchema(**cached_cart)

            # Если данных в кэше нет, пытаемся найти существующую корзину
            cart = await get_cart_with_items(db, user)
            
            if not cart:
                # Создаем новую корзину для авторизованного пользователя
                logger.info("Создание новой корзины для пользователя: user_id=%d", user.id)
                new_cart = CartModel(user_id=user.id)
                db.add(new_cart)
                await db.commit()
                
                # Загружаем созданную корзину с явной загрузкой items (пустой список)
                query = select(CartModel).options(
                    selectinload(CartModel.items)
                ).filter(CartModel.user_id == user.id)
                    
                result = await db.execute(query)
                cart = result.scalars().first()
                
                logger.info("Новая корзина создана: id=%d", cart.id if cart else 'unknown')
            
            # Обогащаем корзину данными о продуктах
            enriched_cart = await enrich_cart_with_product_data(cart)

            # Кладём в кэш
            if enriched_cart:
                await cache_set(cache_key, enriched_cart.model_dump(), CACHE_TTL["cart"])

            logger.info("Корзина пользователя успешно получена: id=%d, items=%d", cart.id, len(cart.items) if hasattr(cart, 'items') and cart.items else 0)
            
            return enriched_cart
            
        # Для анонимных пользователей используем куки
        else:
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
            
            return empty_cart
            
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при получении корзины: %s", str(e))
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

@router.post("/items", response_model=CartResponseSchema, tags=["Корзина"])
async def add_item_to_cart(
    item: CartItemAddSchema,
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Добавляет товар в корзину.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info("Запрос добавления товара в корзину: product_id=%d, quantity=%d, user=%d", item.product_id, item.quantity, user.id if user else 'Anonymous')
    
    # Проверяем наличие товара на складе
    stock_check = await product_api.check_product_stock(item.product_id, item.quantity)
    
    if not stock_check["success"]:
        logger.warning("Ошибка проверки наличия товара: product_id=%d, quantity=%d, error=%s", item.product_id, item.quantity, stock_check.get('error'))
        
        # Если товара на складе недостаточно, но он есть в наличии, добавляем максимально возможное количество
        available_stock = stock_check.get("available_stock", 0)
        if available_stock > 0:
            logger.info("Недостаточно товара, добавляем доступное количество: product_id=%d, requested=%d, available=%d", item.product_id, item.quantity, available_stock)
            # Изменяем количество на максимально доступное
            item.quantity = available_stock
        else:
            # Если товара нет в наличии совсем, возвращаем ошибку
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
            
            # Флаг для отслеживания частичного добавления товара
            partial_add = False
            
            if not cart:
                # Создаем новую корзину
                logger.info("Создание новой корзины: user_id=%d", user.id)
                new_cart = CartModel(user_id=user.id)
                db.add(new_cart)
                await db.commit()
                
                # Загружаем созданную корзину с явной загрузкой items (пустой список)
                query = select(CartModel).options(
                    selectinload(CartModel.items)
                ).filter(CartModel.user_id == user.id)
                    
                result = await db.execute(query)
                cart = result.scalars().first()
                
                logger.info("Новая корзина создана: id=%d", cart.id if cart else 'unknown')
            
            # Проверяем, есть ли уже такой товар в корзине
            existing_item = await CartItemModel.get_item_by_product(db, cart.id, item.product_id)
            
            if existing_item:
                # Проверяем, хватает ли на складе товара с учетом уже имеющегося в корзине
                total_quantity = existing_item.quantity + item.quantity
                stock_check = await product_api.check_product_stock(item.product_id, total_quantity)
                
                if not stock_check["success"]:
                    available_stock = stock_check.get("available_stock", existing_item.quantity)
                    
                    # Если доступно меньше чем уже в корзине, оставляем как есть
                    if available_stock <= existing_item.quantity:
                        return {
                            "success": False,
                            "message": f"В корзине уже максимально доступное количество товара ({existing_item.quantity})",
                            "error": f"Недостаточно товара на складе. Доступно: {available_stock}"
                        }
                    
                    # Если можно добавить хотя бы часть, добавляем сколько можно
                    new_quantity = available_stock
                    logger.info("Недостаточно товара для добавления всего количества: current=%d, requested=%d, new_total=%d", existing_item.quantity, item.quantity, new_quantity)
                    
                    # Обновляем количество до максимально возможного
                    existing_item.quantity = new_quantity
                    existing_item.updated_at = datetime.now()
                    
                    # Флаг для сообщения о частичном добавлении
                    partial_add = True
                else:
                    # Увеличиваем количество
                    logger.info("Обновление существующего товара в корзине: id=%d, новое количество=%d", existing_item.id, existing_item.quantity + item.quantity)
                    existing_item.quantity += item.quantity
                    existing_item.updated_at = datetime.now()
                    partial_add = False
            else:
                # Добавляем новый товар
                logger.info("Добавление нового товара в корзину: product_id=%d, quantity=%d", item.product_id, item.quantity)
                new_item = CartItemModel(
                    cart_id=cart.id,
                    product_id=item.product_id,
                    quantity=item.quantity
                )
                db.add(new_item)
            
            # Обновляем timestamp корзины
            cart.updated_at = datetime.now()
            
            await db.commit()
            # Инвалидируем кэш корзины до получения корзины для ответа
            await invalidate_user_cart_cache(user.id)
            # Загружаем обновленную корзину
            query = select(CartModel).options(
                selectinload(CartModel.items)
            ).filter(CartModel.id == cart.id)
            result = await db.execute(query)
            updated_cart = result.scalars().first()
            await db.refresh(updated_cart, attribute_names=["items"])
            if not updated_cart:
                logger.error("Не удалось получить обновленную корзину после добавления товара")
                return {
                    "success": False,
                    "message": "Ошибка при добавлении товара в корзину",
                    "error": "Не удалось получить обновленную корзину"
                }
            # Обогащаем корзину данными о продуктах
            enriched_cart = await enrich_cart_with_product_data(updated_cart)
            success_message = "Товар успешно добавлен в корзину"
            if partial_add:
                success_message = "Товар добавлен в корзину в максимально доступном количестве"
            return {
                "success": True,
                "message": success_message,
                "cart": enriched_cart
            }
        
        # Для анонимных пользователей используем куки
        else:
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
            
            return empty_cart
            
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при добавлении товара в корзину: %s", str(e))
        return {
            "success": False,
            "message": "Ошибка при добавлении товара в корзину",
            "error": str(e)
        }

@router.put("/items/{item_id}", response_model=CartResponseSchema, tags=["Корзина"])
async def update_cart_item(
    item_id: int,
    item_data: CartItemUpdateSchema,
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Обновляет количество товара в корзине.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info("Запрос обновления количества товара: item_id=%d, quantity=%d, user=%d", item_id, item_data.quantity, user.id if user else 'Anonymous')
    
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
                logger.warning("Элемент корзины не найден: item_id=%d, user_id=%d", item_id, user.id)
                return {
                    "success": False,
                    "message": "Товар не найден в корзине",
                    "error": "Элемент корзины не найден"
                }
            
            # Проверяем доступность товара на складе
            stock_check = await product_api.check_product_stock(cart_item.product_id, item_data.quantity)
            
            if not stock_check["success"]:
                logger.warning("Недостаточно товара на складе: product_id=%d, requested=%d, available=%s", cart_item.product_id, item_data.quantity, stock_check.get('available_stock'))
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
            
            return empty_cart
            
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при обновлении количества товара: %s", str(e))
        return {
            "success": False,
            "message": "Ошибка при обновлении количества товара",
            "error": str(e)
        }

@router.delete("/items/{item_id}", response_model=CartResponseSchema, tags=["Корзина"])
async def remove_cart_item(
    item_id: int,
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Удаляет товар из корзины.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info("Запрос удаления товара из корзины: item_id=%d, user=%d", item_id, user.id if user else 'Anonymous')
    
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
                logger.warning("Элемент корзины не найден: item_id=%d, user_id=%d", item_id, user.id)
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
            
            return empty_cart
            
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при удалении товара из корзины: %s", str(e))
        return {
            "success": False,
            "message": "Ошибка при удалении товара из корзины",
            "error": str(e)
        }

@router.get("/summary", response_model=CartSummarySchema, tags=["Корзина"])
async def get_cart_summary(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Получает сводную информацию о корзине (количество товаров, общая сумма).
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info("Запрос сводной информации о корзине: user=%d", user.id if user else 'Anonymous')
    
    try:
        # Для авторизованных пользователей используем БД и кэш
        if user:
            # Проверяем кэш
            cache_key = f"{CACHE_KEYS['cart_summary_user']}{user.id}"
            cached_summary = await cache_get(cache_key)
            if cached_summary:
                logger.info("Сводка корзины получена из кэша: %s", cache_key)
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
            logger.info("Сводка корзины пользователя сохранена в кэш: %s", cache_key)
            
            return summary
        
        # Для анонимных пользователей используем куки
        else:
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
            
            return empty_cart
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при получении сводной информации о корзине: %s", str(e))
        # В случае ошибки возвращаем пустые данные
        return CartSummarySchema(
            total_items=0,
            total_price=0
        )

@router.delete("", response_model=CartResponseSchema, tags=["Корзина"])
async def clear_cart(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Очищает корзину пользователя.
    Для авторизованных пользователей корзина хранится в БД.
    Для анонимных пользователей корзина хранится в куках.
    """
    logger.info("Запрос очистки корзины: user=%d", user.id if user else 'Anonymous')
    
    try:
        # Для авторизованных пользователей используем БД
        if user:
            # Ищем корзину
            cart = await get_cart_with_items(db, user)
            
            if not cart:
                logger.warning("Корзина не найдена для пользователя: user_id=%d", user.id)
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
            return {
                "success": True,
                "message": "Корзина успешно очищена",
                "cart": empty_cart
            }
            
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при очистке корзины: %s", str(e))
        return {
            "success": False,
            "message": "Ошибка при очистке корзины",
            "error": str(e)
        }

@router.post("/merge", response_model=CartResponseSchema, tags=["Корзина"])
async def merge_carts(
    merge_data: CartMergeSchema,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    logger.info("/cart/merge RAW BODY: %s", merge_data)
    # Удалена проверка дублирования merge-запросов — всегда выполняем объединение

    items = merge_data.items or []
    if not items:
        logger.info("Корзина для объединения пуста, объединение не требуется")
        user_cart = await CartModel.get_user_cart(db, user.id)
        if not user_cart:
            new_cart = CartModel(user_id=user.id)
            db.add(new_cart)
            await db.commit()
            query = select(CartModel).options(selectinload(CartModel.items)).filter(CartModel.user_id == user.id)
            result = await db.execute(query)
            user_cart = result.scalars().first()
        enriched_cart = await enrich_cart_with_product_data(user_cart)
        return {
            "success": True,
            "message": "Корзина не требует объединения",
            "cart": enriched_cart
        }

    user_cart = await CartModel.get_user_cart(db, user.id)
    if not user_cart:
        new_count = len(items)
        updated_count = 0
        new_cart = CartModel(user_id=user.id)
        db.add(new_cart)
        await db.commit()
        query = select(CartModel).options(selectinload(CartModel.items)).filter(CartModel.user_id == user.id)
        result = await db.execute(query)
        user_cart = result.scalars().first()
        logger.info("Новая корзина создана для пользователя: id=%d", user_cart.id)
        for item in items:
            new_item = CartItemModel(
                cart_id=user_cart.id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.add(new_item)
            logger.info("Добавлен товар из localStorage в новую корзину: product_id=%d, quantity=%d", item.product_id, item.quantity)
        await db.commit()
        # Закрываем старую сессию и создаём новую через async_sessionmaker
        await db.close()
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
        db = SessionLocal()
        query = select(CartModel).options(selectinload(CartModel.items)).filter(CartModel.id == user_cart.id)
        result = await db.execute(query)
        user_cart = result.scalars().first()
        enriched_cart = await enrich_cart_with_product_data(user_cart)
        # Только теперь инвалидируем и кладём в кэш
        cache_key = f"{CACHE_KEYS['cart_user']}{user.id}"
        await invalidate_user_cart_cache(user.id)
        await cache_set(cache_key, enriched_cart.model_dump(), CACHE_TTL["cart"])
        logger.info("Корзины успешно объединены: обновлено товаров - %d, добавлено новых - %d", updated_count, new_count)
        return {
            "success": True,
            "message": f"Корзины успешно объединены: обновлено товаров - {updated_count}, добавлено новых - {new_count}",
            "cart": enriched_cart
        }

    logger.info("Объединение корзины из localStorage с корзиной пользователя: user_cart_id=%d, товаров: %d", user_cart.id, len(items))
    updated_count = 0
    new_count = 0
    # --- bulk: собираем все product_id из items и строим мапу существующих CartItem ---
    merge_product_ids = [item.product_id for item in items]
    existing_items = {ci.product_id: ci for ci in user_cart.items if ci.product_id in merge_product_ids}

    for item in items:
        product_id = item.product_id
        quantity = item.quantity
        existing_item = existing_items.get(product_id)
        if existing_item:
            total_quantity = existing_item.quantity + quantity
            stock_check = await product_api.check_product_stock(product_id, total_quantity)
            if stock_check["success"]:
                await db.execute(
                    update(CartItemModel)
                    .where(CartItemModel.id == existing_item.id)
                    .values(quantity=total_quantity, updated_at=datetime.now())
                )
                updated_count += 1
                logger.info("Обновлено количество товара: product_id=%d, новое количество=%d", product_id, total_quantity)
            else:
                available_stock = stock_check.get("available_stock", existing_item.quantity)
                await db.execute(
                    update(CartItemModel)
                    .where(CartItemModel.id == existing_item.id)
                    .values(quantity=available_stock, updated_at=datetime.now())
                )
                updated_count += 1
                logger.info("Обновлено количество товара (ограничено наличием): product_id=%d, новое количество=%d", product_id, available_stock)
        else:
            # --- Защита от дублей: reload user_cart.items из БД и повторно проверить ---
            await db.refresh(user_cart)
            await db.refresh(user_cart, attribute_names=["items"])
            fresh_items = {ci.product_id: ci for ci in user_cart.items}
            fresh_existing = fresh_items.get(product_id)
            if fresh_existing:
                total_quantity = fresh_existing.quantity + quantity
                stock_check = await product_api.check_product_stock(product_id, total_quantity)
                if stock_check["success"]:
                    fresh_existing.quantity = total_quantity
                    fresh_existing.updated_at = datetime.now()
                    updated_count += 1
                    logger.info("(fresh) Обновлено количество товара: product_id=%d, новое количество=%d", product_id, total_quantity)
                else:
                    available_stock = stock_check.get("available_stock", fresh_existing.quantity)
                    fresh_existing.quantity = available_stock
                    fresh_existing.updated_at = datetime.now()
                    updated_count += 1
                    logger.info("(fresh) Обновлено количество товара (ограничено наличием): product_id=%d, новое количество=%d", product_id, available_stock)
                continue
            # --- UPSERT: если всё же возник конфликт, qty увеличится ---
            stmt = insert(CartItemModel).values(
                cart_id=user_cart.id,
                product_id=product_id,
                quantity=quantity
            ).on_conflict_do_update(
                index_elements=['cart_id', 'product_id'],
                set_={
                    'quantity': CartItemModel.quantity + quantity,
                    'updated_at': datetime.now()
                }
            )
            await db.execute(stmt)
            new_count += 1
            logger.info("UPSERT: Добавлен/обновлён товар: product_id=%d, количество=%d", product_id, quantity)
    # Сохраняем обновления
    user_cart.updated_at = datetime.now()
    await db.commit()
    # Закрываем старую сессию и создаём новую через async_sessionmaker
    await db.close()
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    db = SessionLocal()
    query = select(CartModel).options(selectinload(CartModel.items)).filter(CartModel.id == user_cart.id)
    result = await db.execute(query)
    user_cart = result.scalars().first()
    enriched_cart = await enrich_cart_with_product_data(user_cart)
    # Только теперь инвалидируем и кладём в кэш
    cache_key = f"{CACHE_KEYS['cart_user']}{user.id}"
    await invalidate_user_cart_cache(user.id)
    await cache_set(cache_key, enriched_cart.model_dump(), CACHE_TTL["cart"])
    logger.info("Корзины успешно объединены: обновлено товаров - %d, добавлено новых - %d", updated_count, new_count)
    return {
        "success": True,
        "message": f"Корзины успешно объединены: обновлено товаров - {updated_count}, добавлено новых - {new_count}",
        "cart": enriched_cart
    }