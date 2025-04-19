from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional, Annotated
import os
import logging
import fastapi

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

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.post('/batch', tags=["Products"])
async def get_products_batch(
    session: SessionDep,
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов"),
    current_user: User = Depends(get_current_user),
    service_key: Optional[str] = Header(None, alias="service-key", description="Секретный ключ для доступа к API (альтернатива авторизации)")
):
    """
    Получить информацию о нескольких продуктах по их ID.
    Возвращает список объектов продуктов для всех найденных ID.
    Требуются права администратора или валидный ключ сервиса.
    """
    logger.info(f"Пакетный запрос информации о продуктах: {product_ids}")
    logger.info(f"Заголовок service-key: '{service_key}'")    
    # Проверка авторизации: или авторизованный пользователь с правами администратора или валидный ключ сервиса
    INTERNAL_SERVICE_KEY = "test"  # Жестко задаем значение для тестирования
    logger.info(f"Ожидаемый ключ сервиса: '{INTERNAL_SERVICE_KEY}'")
    
    authorized = False
    
    # Проверка через ключ сервиса с маленькой буквы
    if service_key and service_key.strip('"') == INTERNAL_SERVICE_KEY:
        logger.info("Авторизация через ключ сервиса (service-key) успешна")
        authorized = True
    # Проверка через пользователя
    elif current_user:
        if getattr(current_user, 'is_admin', False) or getattr(current_user, 'is_super_admin', False):
            logger.info(f"Авторизация через пользователя {current_user.id} успешна")
            authorized = True
        else:
            logger.warning(f"Пользователь {current_user.id} пытался получить пакетный доступ к продуктам без прав администратора")
    
    if not authorized:
        logger.error("Не авторизован: ни через ключ сервиса, ни через пользователя")
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    if not product_ids:
        return []
    
    # Убираем дубликаты и ограничиваем размер запроса
    unique_ids = list(set(product_ids))
    if len(unique_ids) > 100:  # Ограничиваем количество запрашиваемых продуктов
        logger.warning(f"Слишком много ID продуктов в запросе ({len(unique_ids)}), ограничиваем до 100")
        unique_ids = unique_ids[:100]
    
    try:
        # Создаем запрос для получения всех продуктов по их ID
        query = select(ProductModel).filter(ProductModel.id.in_(unique_ids))
        result = await session.execute(query)
        products = result.scalars().all()
        
        logger.info(f"Найдено {len(products)} продуктов из {len(unique_ids)} запрошенных")
        
        # Преобразуем продукты в JSON-совместимый формат
        return products
    except Exception as e:
        logger.error(f"Ошибка при выполнении пакетного запроса продуктов: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.post('/public-batch', tags=["Products"])
async def get_products_public_batch(
    session: SessionDep,
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов"),
    service_key: str = Header(..., alias="service-key", description="Секретный ключ для доступа к API")
):
    """
    Публичный API для получения информации о нескольких продуктах по их ID.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_ids**: Список ID продуктов
    - **service_key**: Секретный ключ для доступа к API (передается в заголовке)
    """
    # Проверяем секретный ключ (должен совпадать с ключом в конфигурации)
    INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")
    if service_key != INTERNAL_SERVICE_KEY:
        logger.warning(f"Попытка доступа к публичному batch API с неверным ключом: {service_key[:5]}...")
        raise HTTPException(
            status_code=403, 
            detail="Доступ запрещен: неверный ключ сервиса"
        )
    
    logger.info(f"Публичный пакетный запрос информации о продуктах: {product_ids}")
    
    if not product_ids:
        return []
    
    # Убираем дубликаты и ограничиваем размер запроса
    unique_ids = list(set(product_ids))
    if len(unique_ids) > 100:  # Ограничиваем количество запрашиваемых продуктов
        logger.warning(f"Слишком много ID продуктов в запросе ({len(unique_ids)}), ограничиваем до 100")
        unique_ids = unique_ids[:100]
    
    try:
        # Создаем запрос для получения всех продуктов по их ID
        query = select(ProductModel).filter(ProductModel.id.in_(unique_ids))
        result = await session.execute(query)
        products = result.scalars().all()
        
        logger.info(f"Найдено {len(products)} продуктов из {len(unique_ids)} запрошенных (публичный API)")
        
        # Преобразуем продукты в JSON-совместимый формат
        return products
    except Exception as e:
        logger.error(f"Ошибка при выполнении публичного пакетного запроса продуктов: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.post('/open-batch', tags=["Products"])
async def get_products_open_batch(
    session: SessionDep,
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов")
):
    """
    Новый публичный batch-эндпоинт: получить список продуктов по id без авторизации и service-key.
    Ограничение: не более 100 id за раз.
    """
    logger.info(f"Открытый batch-запрос продуктов: {product_ids}")
    if not product_ids:
        return []
    unique_ids = list(set(product_ids))
    if len(unique_ids) > 100:
        logger.warning(f"Слишком много ID продуктов в запросе ({len(unique_ids)}), ограничиваем до 100")
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
        logger.info(f"Обновлено количество товара ID={product_id}: {old_stock} -> {new_stock} администратором {admin.get('user_id')}")
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при обновлении количества товара: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}")

@router.put("/{product_id}/public-stock", status_code=200)
async def update_product_public_stock(
    product_id: int,
    session: SessionDep,
    data: dict = Body(..., description="Данные для обновления остатка"),
    service_key: str = Header(..., alias="service-key", description="Секретный ключ для доступа к API")
):
    """
    Публичный API для обновления количества товара на складе.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_id**: ID продукта
    - **data**: Данные для обновления (должны содержать поле 'stock')
    - **service_key**: Секретный ключ для доступа к API (передается в заголовке)
    """
    # Проверяем секретный ключ (должен совпадать с ключом в конфигурации)
    INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")
    if service_key != INTERNAL_SERVICE_KEY:
        logger.warning(f"Попытка доступа к публичному API с неверным ключом: {service_key[:5]}...")
        raise HTTPException(
            status_code=403, 
            detail="Доступ запрещен: неверный ключ сервиса"
        )
    
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
        logger.info(f"Публичное обновление количества товара ID={product_id}: {old_stock} -> {new_stock} через сервисный ключ")
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при публичном обновлении количества товара: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}")

@router.put("/{product_id}/admin-stock", status_code=200)
async def update_product_admin_stock(
    product_id: int,
    session: SessionDep,
    data: dict = Body(..., description="Данные для обновления остатка"),
    service_key: str = Header(..., alias="Service-Key", description="Секретный ключ для доступа к API")
):
    """
    Админский API для обновления количества товара на складе без ограничений.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_id**: ID продукта
    - **data**: Данные для обновления (должны содержать поле 'stock')
    - **service_key**: Секретный ключ для доступа к API (передается в заголовке Service-Key)
    """
    # Проверяем секретный ключ (должен совпадать с ключом в конфигурации)
    INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")
    # Для тестирования жестко кодируем значение
    INTERNAL_SERVICE_KEY = "test"
    
    logger.info(f"Запрос на админское обновление остатка товара {product_id} с ключом {service_key}")
    
    if service_key != INTERNAL_SERVICE_KEY:
        logger.warning(f"Попытка доступа к админскому API с неверным ключом: {service_key}")
        raise HTTPException(
            status_code=403, 
            detail="Доступ запрещен: неверный ключ сервиса"
        )
    
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
        logger.info(f"Админское обновление количества товара ID={product_id}: {old_stock} -> {new_stock} через сервисный ключ")
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при админском обновлении количества товара: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}")
