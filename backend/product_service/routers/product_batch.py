"""
Роуты для пакетных операций с продуктами (batch endpoints).
"""

from typing import List, Annotated
import os
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt


from models import ProductModel
from database import get_session
from auth import User, get_current_user, require_admin
from cache import cache_delete_pattern, CACHE_KEYS, invalidate_cache

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_batch_router")

# Создание роутера
router = APIRouter(
    prefix="/products",
    tags=["product_batches"],
    responses={404: {"description": "Not found"}},
)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


bearer_scheme = HTTPBearer(auto_error=False)
async def verify_service_jwt(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> bool:
    """Проверяет JWT токен с scope 'service'"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.post('/batch', tags=["Products"])
async def get_products_batch(
    session: SessionDep,
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов"),
    current_user: User = Depends(get_current_user),
    dependencies=[Depends(verify_service_jwt)]
):
    """
    Получить информацию о нескольких продуктах по их ID.
    Возвращает список объектов продуктов для всех найденных ID.
    Требуются права администратора или валидный ключ сервиса.
    """
    logger.info("Пакетный запрос информации о продуктах: %s", product_ids)
    
    authorized = False
    
    # Проверка через ключ сервиса с маленькой буквы
    if dependencies:
        logger.info("Авторизация через ключ сервиса (dependencies) успешна")
        authorized = True
    # Проверка через пользователя
    elif current_user:
        if getattr(current_user, 'is_admin', False) or getattr(current_user, 'is_super_admin', False):
            logger.info("Авторизация через пользователя %s успешна", current_user.id)
            authorized = True
        else:
            logger.warning("Пользователь %s пытался получить пакетный доступ к продуктам без прав администратора", current_user.id)
    
    if not authorized:
        logger.error("Не авторизован: ни через ключ сервиса, ни через пользователя")
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    if not product_ids:
        return []
    
    # Убираем дубликаты и ограничиваем размер запроса
    unique_ids = list(set(product_ids))
    if len(unique_ids) > 100:  # Ограничиваем количество запрашиваемых продуктов
        logger.warning("Слишком много ID продуктов в запросе (%s), ограничиваем до 100", len(unique_ids))
        unique_ids = unique_ids[:100]
    
    try:
        # Создаем запрос для получения всех продуктов по их ID
        query = select(ProductModel).filter(ProductModel.id.in_(unique_ids))
        result = await session.execute(query)
        products = result.scalars().all()
        
        logger.info("Найдено %s продуктов из %s запрошенных", len(products), len(unique_ids))
        
        # Преобразуем продукты в JSON-совместимый формат
        return products
    except Exception as e:
        logger.error("Ошибка при выполнении пакетного запроса продуктов: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}") from e

@router.post('/public-batch', tags=["Products"],dependencies=[Depends(verify_service_jwt)])
async def get_products_public_batch(
    session: SessionDep,
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов"),
):
    """
    Публичный API для получения информации о нескольких продуктах по их ID.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_ids**: Список ID продуктов
    """    
    logger.info("Публичный пакетный запрос информации о продуктах: %s", product_ids)
    
    if not product_ids:
        return []
    
    # Убираем дубликаты и ограничиваем размер запроса
    unique_ids = list(set(product_ids))
    if len(unique_ids) > 100:  # Ограничиваем количество запрашиваемых продуктов
        logger.warning("Слишком много ID продуктов в запросе (%s), ограничиваем до 100", len(unique_ids))
        unique_ids = unique_ids[:100]
    
    try:
        # Создаем запрос для получения всех продуктов по их ID
        query = select(ProductModel).filter(ProductModel.id.in_(unique_ids))
        result = await session.execute(query)
        products = result.scalars().all()
        
        logger.info("Найдено %s продуктов из %s запрошенных (публичный API)", len(products), len(unique_ids))
        
        # Преобразуем продукты в JSON-совместимый формат
        return products
    except Exception as e:
        logger.error("Ошибка при выполнении публичного пакетного запроса продуктов: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}") from e

@router.post('/open-batch', tags=["Products"])
async def get_products_open_batch(
    session: SessionDep,
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов")
):
    """
    Новый публичный batch-эндпоинт: получить список продуктов по id без авторизации и service-key.
    Ограничение: не более 100 id за раз.
    """
    logger.info("Открытый batch-запрос продуктов: %s", product_ids)
    if not product_ids:
        return []
    unique_ids = list(set(product_ids))
    if len(unique_ids) > 100:
        logger.warning("Слишком много ID продуктов в запросе (%s), ограничиваем до 100", len(unique_ids))
        unique_ids = unique_ids[:100]
    query = select(ProductModel).where(ProductModel.id.in_(unique_ids))
    result = await session.execute(query)
    products = result.scalars().all()
    # Если нужна подробная инфа (связи) — раскомментируй:
    # return [await ProductModel.get_product_with_relations(session, p.id) for p in products]
    return products

@router.put("/{product_id}/stock", status_code=200)
async def update_product_stock(
    product_id: int,
    session: SessionDep,
    data: dict = Body(..., description="Данные для обновления остатка"),
    admin: dict = Depends(require_admin)
):
    """
    Обновление количества товара на складе (только для администраторов).
    
    - **product_id**: ID продукта
    - **data**: Данные для обновления (должны содержать поле 'stock')
    """
    # Проверяем наличие обязательного поля
    if 'stock' not in data:
        raise HTTPException(status_code=400, detail="Поле 'stock' обязательно")
    
    new_stock = data['stock']
    if not isinstance(new_stock, int) or new_stock < 0:
        raise HTTPException(status_code=400, detail="Поле 'stock' должно быть неотрицательным целым числом")
    
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    
    try:
        # Обновляем количество товара
        old_stock = product.stock
        product.stock = new_stock
        await session.commit()
        await session.refresh(product)
        
        # Инвалидация кэша продукта
        await cache_delete_pattern(f"{CACHE_KEYS['products']}detail:{product_id}")
        # Инвалидация всего кэша продуктов для обновления списков
        await invalidate_cache("products")
        logger.info("Обновлено количество товара ID=%s: %s -> %s администратором %s", product_id, old_stock, new_stock, admin.get('user_id'))
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error("Ошибка при обновлении количества товара: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}") from e

@router.put("/{product_id}/public-stock", status_code=200,dependencies=[Depends(verify_service_jwt)])
async def update_product_public_stock(
    product_id: int,
    session: SessionDep,
    data: dict = Body(..., description="Данные для обновления остатка"),
):
    """
    Публичный API для обновления количества товара на складе.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_id**: ID продукта
    - **data**: Данные для обновления (должны содержать поле 'stock')
    """
    # Проверяем наличие обязательного поля
    if 'stock' not in data:
        raise HTTPException(status_code=400, detail="Поле 'stock' обязательно")
    
    new_stock = data['stock']
    if not isinstance(new_stock, int) or new_stock < 0:
        raise HTTPException(status_code=400, detail="Поле 'stock' должно быть неотрицательным целым числом")
    
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    
    # В публичном API разрешаем только уменьшать количество товара
    # Это предотвращает возможность накручивать количество через публичный API
    if new_stock > product.stock:
        raise HTTPException(
            status_code=400, 
            detail="Через публичный API можно только уменьшать количество товара"
        )
    
    try:
        # Обновляем количество товара
        old_stock = product.stock
        product.stock = new_stock
        await session.commit()
        await session.refresh(product)
        
        # Инвалидация кэша продукта
        await cache_delete_pattern(f"{CACHE_KEYS['products']}detail:{product_id}")
        # Инвалидация всего кэша продуктов для обновления списков
        await invalidate_cache("products")
        logger.info("Публичное обновление количества товара ID=%s: %s -> %s через сервисный ключ", product_id, old_stock, new_stock)
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error("Ошибка при публичном обновлении количества товара: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}") from e

@router.put("/{product_id}/admin-stock", status_code=200,dependencies=[Depends(verify_service_jwt)])
async def update_product_admin_stock(
    product_id: int,
    session: SessionDep,
    data: dict = Body(..., description="Данные для обновления остатка"),
):
    """
    Админский API для обновления количества товара на складе без ограничений.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_id**: ID продукта
    - **data**: Данные для обновления (должны содержать поле 'stock')
    """
    
    # Проверяем наличие обязательного поля
    if 'stock' not in data:
        raise HTTPException(status_code=400, detail="Поле 'stock' обязательно")
    
    new_stock = data['stock']
    if not isinstance(new_stock, int) or new_stock < 0:
        raise HTTPException(status_code=400, detail="Поле 'stock' должно быть неотрицательным целым числом")
    
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    
    # В админском API разрешаем изменять количество товара без ограничений
    try:
        # Обновляем количество товара
        old_stock = product.stock
        product.stock = new_stock
        await session.commit()
        await session.refresh(product)
        
        # Инвалидация кэша продукта
        await cache_delete_pattern(f"{CACHE_KEYS['products']}detail:{product_id}")
        # Инвалидация всего кэша продуктов для обновления списков
        await invalidate_cache("products")
        logger.info("Админское обновление количества товара ID=%s: %s -> %s через сервисный ключ", product_id, old_stock, new_stock)
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error("Ошибка при админском обновлении количества товара: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}") from e
