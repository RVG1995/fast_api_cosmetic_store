"""
Роутер для админки корзин
"""

from typing import Optional
import logging

from fastapi import Depends, HTTPException, Query, APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import SQLAlchemyError
from models import CartModel
from database import get_session
from auth import User, get_current_admin_user
from schema import (UserCartSchema, PaginatedUserCartsResponse, UserCartItemSchema)
from product_api import ProductAPI
from cache import (cache_get, cache_set,CACHE_KEYS, CACHE_TTL)
from auth import get_user_info

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_service")


# Инициализация ProductAPI
product_api = ProductAPI()

# Создание роутера
router = APIRouter(
    prefix="/admin/carts",
    tags=["admin_carts"],
    responses={404: {"description": "Not found"}},
)



@router.get("", response_model=PaginatedUserCartsResponse, tags=["Администрирование"],dependencies=[Depends(get_current_admin_user)])
async def get_user_carts(
    page: int = Query(1, description="Номер страницы", ge=1),
    limit: int = Query(10, description="Количество записей на странице", ge=1, le=100),
    sort_by: str = Query("updated_at", description="Поле для сортировки", pattern="^(id|user_id|created_at|updated_at|items_count|total_price)$"),
    sort_order: str = Query("desc", description="Порядок сортировки", pattern="^(asc|desc)$"),
    user_id: Optional[int] = Query(None, description="Фильтр по ID пользователя"),
    filter: Optional[str] = Query(None, description="Фильтр (with_items/empty)"),
    search: Optional[str] = Query(None, description="Поисковый запрос по ID корзины"),
    db: AsyncSession = Depends(get_session),
    request: Request = None,
):
    """
    Получает список всех корзин пользователей (для администраторов)
    """
    logger.info("Запрос списка корзин пользователей: page=%d, limit=%d, sort_by=%s, sort_order=%s, user_id=%s, filter=%s", page, limit, sort_by, sort_order, str(user_id) if user_id is not None else "None", filter)
    
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['admin_carts']}page:{page}:limit:{limit}:sort:{sort_by}:{sort_order}:user:{user_id}:filter:{filter}:search:{search}"
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.info("Список корзин получен из кэша: %s", cache_key)
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
            admin_bearer = request.headers.get("Authorization") if request else None
            if (not admin_bearer or not admin_bearer.startswith("Bearer ")) and request:
                cookie_token = request.cookies.get("access_token")
                if cookie_token:
                    admin_bearer = f"Bearer {cookie_token}"
            user_info = await get_user_info(cart.user_id, admin_bearer=admin_bearer) if cart.user_id else {}
            first_name = user_info.get('first_name', '')
            last_name = user_info.get('last_name', '')
            user_name = f"{first_name} {last_name}".strip() or f"Пользователь {cart.user_id}"
            
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
                user_name=user_name,
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
        logger.info("Список корзин сохранен в кэш: %s", cache_key)
        
        return result
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при получении списка корзин: %s", str(e))
        return PaginatedUserCartsResponse(
            items=[],
            total=0,
            page=page,
            limit=limit,
            pages=1
        )
    except Exception as e:
        logger.error("Необработанная ошибка при получении списка корзин: %s", str(e))
        return PaginatedUserCartsResponse(
            items=[],
            total=0,
            page=page,
            limit=limit,
            pages=1
        )

@router.get("/{cart_id}", response_model=UserCartSchema, tags=["Администрирование"])
async def get_user_cart_by_id(
    cart_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_session),
    request: Request = None,
):
    """
    Получает информацию о конкретной корзине пользователя (для администратора)
    """
    logger.info("Запрос информации о корзине ID=%d администратором %d", cart_id, current_user.id)
    
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['admin_carts']}cart:{cart_id}"
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.info("Информация о корзине ID=%d получена из кэша", cart_id)
            return UserCartSchema(**cached_data)
        
        # Получаем корзину по ID с загрузкой элементов
        cart = await CartModel.get_by_id(db, cart_id)
        
        if not cart:
            logger.warning("Корзина с ID=%d не найдена", cart_id)
            raise HTTPException(status_code=404, detail="Корзина не найдена")
        
        # Получаем дополнительную информацию о пользователе
        user_info = None
        if cart.user_id:
            admin_bearer = request.headers.get("Authorization") if request else None
            if (not admin_bearer or not admin_bearer.startswith("Bearer ")) and request:
                cookie_token = request.cookies.get("access_token")
                if cookie_token:
                    admin_bearer = f"Bearer {cookie_token}"
            user_info = await get_user_info(cart.user_id, admin_bearer=admin_bearer)
        
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
        if user_info:
            first_name = user_info.get('first_name', '')
            last_name = user_info.get('last_name', '')
            user_name = f"{first_name} {last_name}".strip() or f"Пользователь {cart.user_id}"
        else:
            user_name = f"Пользователь {cart.user_id}"

        result = UserCartSchema(
            id=cart.id,
            user_id=cart.user_id,
            user_email=user_info.get("email") if user_info else None,
            user_name=user_name,
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
        logger.info("Информация о корзине ID=%d сохранена в кэш", cart_id)
        
        return result
        
    except HTTPException as e:
        logger.error("HTTP ошибка при получении информации о корзине ID=%d: %s", cart_id, str(e))
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except (SQLAlchemyError, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при получении информации о корзине ID=%d: %s", cart_id, str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}") from e
    except Exception as e:
        logger.error("Необработанная ошибка при получении информации о корзине ID=%d: %s", cart_id, str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}") from e