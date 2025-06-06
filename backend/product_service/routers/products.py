"""Роуты для работы с продуктами в сервисе товаров."""

import uuid
import os
import logging
from typing import List, Optional, Annotated, Dict

from fastapi import Depends, HTTPException, UploadFile, File, Form, Query, Body,APIRouter, status
from database import get_session
from models import ProductModel
from auth import require_admin, get_current_user
from schema import ProductAddSchema,ProductSchema, PaginatedProductResponse, ProductDetailSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from cache import cache_get, cache_set, cache_delete_pattern, invalidate_cache, CACHE_KEYS, DEFAULT_CACHE_TTL

# Определяем директорию для сохранения изображений
UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_service")

# Создание роутера
router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={404: {"description": "Not found"}},
)

# Создание роутера для админ-панели
admin_router = APIRouter(
    prefix="/admin/products",
    tags=["admin_products"],
    responses={404: {"description": "Not found"}},
)

SessionDep = Annotated[AsyncSession,Depends(get_session)]

@router.post("", response_model=ProductSchema, status_code=201,dependencies=[Depends(require_admin)])
async def add_product(
    name: str = Form(...),
    price: str = Form(...),
    description: Optional[str] = Form(None),
    stock: str = Form(...),
    category_id: str = Form(...),
    subcategory_id: Optional[str] = Form(None),
    country_id: str = Form(...),
    brand_id: str = Form(...),
    image: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session)
):
    """Добавление нового продукта."""
    logger.info("Получен запрос на создание продукта: %s, цена: %s", name, price)
    logger.info("Параметры: description=%s, stock=%s, category_id=%s, subcategory_id=%s, country_id=%s, brand_id=%s", description, stock, category_id, subcategory_id, country_id, brand_id)
    logger.info("Изображение: %s", image and image.filename)

    # Конвертация строковых значений в нужные типы
    try:
        price_int = int(price)
        stock_int = int(stock)
        category_id_int = int(category_id)
        subcategory_id_int = int(subcategory_id) if subcategory_id else None
        country_id_int = int(country_id)
        brand_id_int = int(brand_id)
    except ValueError as e:
        logger.error("Ошибка конвертации типов: %s", str(e))
        raise HTTPException(status_code=422, detail=f"Некорректный формат данных: {str(e)}") from e

    # Если image равен None, принудительно делаем его None
    if not image:
        image = None
        logger.info("Изображение не предоставлено")

    image_url = None
    if image:
        try:
            logger.info("Обработка изображения: %s", image.filename)
            extension = os.path.splitext(image.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())
            
            image_url = f"/static/images/{unique_filename}"
            logger.info("Изображение сохранено по пути: %s", image_url)
        except Exception as e:
            logger.error("Ошибка при сохранении изображения: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Ошибка при сохранении изображения: {str(e)}") from e

    try:
        product_data = ProductAddSchema(
            name=name,
            price=price_int,
            description=description,
            stock=stock_int,
            category_id=category_id_int,
            subcategory_id=subcategory_id_int,
            country_id=country_id_int,
            brand_id=brand_id_int,
            image=image_url
        )
        
        product = ProductModel(
            name=product_data.name,
            price=product_data.price,
            description=product_data.description,
            stock=product_data.stock,
            category_id=product_data.category_id,
            subcategory_id=product_data.subcategory_id,
            country_id=product_data.country_id,
            brand_id=product_data.brand_id,
            image=product_data.image
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        
        # Инвалидация кэша продуктов после добавления нового продукта
        await invalidate_cache("products")
        logger.info("Продукт успешно создан: ID=%s, кэш продуктов инвалидирован", product.id)
        
        return product
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        logger.error("Ошибка целостности данных: %s", error_detail)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}") from e
    except Exception as e:
        logger.error("Непредвиденная ошибка: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при создании продукта: {str(e)}") from e

@router.get('', response_model=PaginatedProductResponse)
async def get_products(
    session: SessionDep,
    page: int = Query(1, description="Текущая страница пагинации"),
    limit: int = Query(10, description="Количество записей на страницу"),
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    subcategory_id: Optional[int] = Query(None, description="ID подкатегории для фильтрации"),
    brand_id: Optional[int] = Query(None, description="ID бренда для фильтрации"),
    country_id: Optional[int] = Query(None, description="ID страны для фильтрации"),
    sort: Optional[str] = Query(None, description="Сортировка (newest, price_asc, price_desc)"),
):
    """Получение списка продуктов с пагинацией."""
    # Формируем ключ кэша на основе параметров запроса
    cache_key = f"{CACHE_KEYS['products']}list:page={page}:limit={limit}:cat={category_id}:subcat={subcategory_id}:brand={brand_id}:country={country_id}:sort={sort}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Данные о продуктах получены из кэша: page=%s, limit=%s", page, limit)
        return cached_data
    
    # Расчет пропуска записей для пагинации
    skip = (page - 1) * limit
    
    # Подготавливаем фильтры
    filter_criteria = {}
    if category_id is not None:
        filter_criteria['category_id'] = category_id
    if subcategory_id is not None:
        filter_criteria['subcategory_id'] = subcategory_id
    if brand_id is not None:
        filter_criteria['brand_id'] = brand_id
    if country_id is not None:
        filter_criteria['country_id'] = country_id
    
    # Используем оптимизированный метод для получения продуктов и их связанных данных
    products, total = await ProductModel.get_products_with_relations(
        session=session,
        filter_criteria=filter_criteria,
        limit=limit,
        offset=skip,
        sort=sort,
        only_in_stock=True
    )
    
    # Формируем ответ с информацией о пагинации
    response_data = {
        "total": total,
        "limit": limit,
        "offset": skip,
        "items": products
    }
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, response_data)
    logger.info("Данные о продуктах сохранены в кэш: page=%s, limit=%s, total=%s", page, limit, total)
    
    return response_data

@router.get('/admin', response_model=PaginatedProductResponse,dependencies=[Depends(require_admin)])
async def get_admin_products(
    session: SessionDep,
    page: int = Query(1, description="Текущая страница пагинации"),
    limit: int = Query(10, description="Количество записей на страницу"),
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    subcategory_id: Optional[int] = Query(None, description="ID подкатегории для фильтрации"),
    brand_id: Optional[int] = Query(None, description="ID бренда для фильтрации"),
    country_id: Optional[int] = Query(None, description="ID страны для фильтрации"),
    sort: Optional[str] = Query(None, description="Сортировка (newest, price_asc, price_desc)"),
):
    """Получение списка продуктов для администратора."""
    # Формируем ключ кэша на основе параметров запроса
    cache_key = f"{CACHE_KEYS['products']}admin:page={page}:limit={limit}:cat={category_id}:subcat={subcategory_id}:brand={brand_id}:country={country_id}:sort={sort}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Админские данные о продуктах получены из кэша: page=%s, limit=%s", page, limit)
        return cached_data
    
    # Расчет пропуска записей для пагинации
    skip = (page - 1) * limit
    
    # Подготавливаем фильтры
    filter_criteria = {}
    if category_id is not None:
        filter_criteria['category_id'] = category_id
    if subcategory_id is not None:
        filter_criteria['subcategory_id'] = subcategory_id
    if brand_id is not None:
        filter_criteria['brand_id'] = brand_id
    if country_id is not None:
        filter_criteria['country_id'] = country_id
    
    # Используем оптимизированный метод для получения продуктов и их связанных данных
    # Для администратора показываем все товары, включая те, которых нет в наличии
    products, total = await ProductModel.get_products_with_relations(
        session=session,
        filter_criteria=filter_criteria,
        limit=limit,
        offset=skip,
        sort=sort,
        only_in_stock=False  # Показываем все товары для админа
    )
    
    # Формируем ответ с информацией о пагинации
    response_data = {
        "total": total,
        "limit": limit,
        "offset": skip,
        "items": products
    }
    
    # Сохраняем данные в кэш с уменьшенным TTL для админского интерфейса
    # Для админского интерфейса устанавливаем меньшее время жизни кэша, чтобы данные быстрее обновлялись
    await cache_set(cache_key, response_data, DEFAULT_CACHE_TTL // 2)
    logger.info("Админские данные о продуктах сохранены в кэш: page=%s, limit=%s, total=%s", page, limit, total)
    
    return response_data

@router.get('/search', response_model=List[dict])
async def search_products(session: SessionDep, name: str):
    """
    Поиск товаров по имени с использованием оператора LIKE.
    Возвращает только базовую информацию для карточек товаров.
    """
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['products']}search:{name}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Результаты поиска '%s' получены из кэша: %s товаров", name, len(cached_data))
        return cached_data
    
    # Формируем поисковый запрос с использованием LIKE
    search_term = f"%{name}%"
    
    # Создаем запрос к базе данных с предварительной загрузкой связанных данных
    query = select(ProductModel).options(
        selectinload(ProductModel.category),
        selectinload(ProductModel.brand)
    ).filter(
        ProductModel.name.ilike(search_term)
    ).order_by(ProductModel.id.desc()).limit(10)
    
    # Выполняем запрос
    result = await session.execute(query)
    products = result.scalars().all()
    
    # Формируем упрощенный список товаров с базовой информацией
    response_list = []
    
    for product in products:
        # Создаем словарь только с необходимыми данными товара для карточки
        product_dict = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "image": product.image,
            "stock": product.stock,
            "brand": product.brand.name if product.brand else None,
            "category": product.category.name if product.category else None
        }
        
        # Добавляем продукт в список ответа
        response_list.append(product_dict)
    
    # Сохраняем результаты в кэш с меньшим TTL, так как поисковые запросы часто меняются
    await cache_set(cache_key, response_list, DEFAULT_CACHE_TTL // 2)
    logger.info("Результаты поиска '%s' сохранены в кэш: %s товаров", name, len(response_list))
    
    return response_list

@router.get('/{product_id}',response_model = ProductDetailSchema)
async def get_product_id(product_id: int, session: SessionDep):
    """Получение информации о продукте по его ID."""
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['products']}detail:{product_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Данные о продукте ID=%s получены из кэша", product_id)
        return cached_data
    
    # Используем оптимизированный метод для получения продукта с его связанными данными
    product = await ProductModel.get_product_with_relations(session, product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Создаем словарь с данными товара
    response_dict = {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "description": product.description,
        "stock": product.stock,
        "category_id": product.category_id,
        "subcategory_id": product.subcategory_id,
        "country_id": product.country_id,
        "brand_id": product.brand_id,
        "image": product.image,
        "category": None,
        "subcategory": None,
        "brand": None,
        "country": None
    }
    
    # Преобразуем связанные данные из загруженных объектов
    if product.category:
        response_dict["category"] = {
            "id": product.category.id,
            "name": product.category.name,
            "slug": product.category.slug
        }
    
    if product.subcategory:
        response_dict["subcategory"] = {
            "id": product.subcategory.id,
            "name": product.subcategory.name,
            "slug": product.subcategory.slug,
            "category_id": product.subcategory.category_id
        }
    
    if product.brand:
        response_dict["brand"] = {
            "id": product.brand.id,
            "name": product.brand.name,
            "slug": product.brand.slug
        }
    
    if product.country:
        response_dict["country"] = {
            "id": product.country.id,
            "name": product.country.name,
            "slug": product.country.slug
        }
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, response_dict)
    logger.info("Данные о продукте ID=%s сохранены в кэш", product_id)
    
    return response_dict

@router.put("/{product_id}/form", response_model=ProductSchema,dependencies=[Depends(require_admin)])
async def update_product_form(
    product_id: int,
    name: Optional[str] = Form(None),
    price: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    stock: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    subcategory_id: Optional[str] = Form(None),
    country_id: Optional[str] = Form(None),
    brand_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session)
):
    """Обновление продукта."""
    logger.info("Получен запрос на обновление продукта ID=%s", product_id)
    logger.info("Параметры: name=%s, price=%s, description=%s, stock=%s", name, price, description, stock)
    logger.info("category_id=%s, subcategory_id=%s, country_id=%s, brand_id=%s", category_id, subcategory_id, country_id, brand_id)
    logger.info("Изображение: %s", image and image.filename)
    
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        logger.error("Продукт с ID=%s не найден", product_id)
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        # Обновляем все поля напрямую, без создания промежуточного словаря
        # Поле обновляется только если значение было предоставлено (не None)
        
        # Обновляем текстовые поля
        if name is not None:
            product.name = name
            
        if description is not None:
            product.description = description
            
        # Конвертируем и обновляем числовые поля
        if price is not None:
            product.price = int(price)
            
        if stock is not None:
            product.stock = int(stock)
            
        if category_id is not None:
            product.category_id = int(category_id)
            
        # Особая обработка для subcategory_id
        if subcategory_id is not None:
            if subcategory_id == "":
                # Если передана пустая строка, явно устанавливаем None
                product.subcategory_id = None
                logger.info("subcategory_id установлен в None для продукта ID=%s", product_id)
            else:
                product.subcategory_id = int(subcategory_id)
                logger.info("subcategory_id установлен в %s для продукта ID=%s", subcategory_id, product_id)
                
        if country_id is not None:
            product.country_id = int(country_id)
            
        if brand_id is not None:
            product.brand_id = int(brand_id)
            
        # Обработка изображения
        if image:
            extension = os.path.splitext(image.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())
            
            product.image = f"/static/images/{unique_filename}"
            logger.info("Изображение сохранено по пути: %s", product.image)
            
        # Сохраняем обновленный продукт
        await session.commit()
        await session.refresh(product)
        
        # Инвалидация кэша продуктов
        await invalidate_cache("products")
        # Инвалидация кэша конкретного продукта
        await cache_delete_pattern(f"{CACHE_KEYS['products']}detail:{product_id}")
        # Инвалидация кэша в формате cart_service для конкретного продукта
        await cache_delete_pattern(f"product:{product_id}")
        logger.info("Продукт ID=%s успешно обновлен, кэш продуктов инвалидирован", product_id)
        
        return product
        
    except ValueError as e:
        await session.rollback()
        logger.error("Ошибка конвертации типов: %s", str(e))
        raise HTTPException(status_code=422, detail=f"Некорректный формат данных: {str(e)}") from e
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        logger.error("Ошибка целостности данных: %s", error_detail)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}") from e
    except Exception as e:
        await session.rollback()
        logger.error("Непредвиденная ошибка при обновлении продукта: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении продукта: {str(e)}") from e

@router.delete("/{product_id}", status_code=204,dependencies=[Depends(require_admin)])
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Удаление продукта."""
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Удаляем продукт
    try:
        await session.delete(product)
        await session.commit()
        
        # Инвалидация кэша продуктов
        await invalidate_cache("products")
        # Инвалидация кэша в формате cart_service для конкретного продукта
        await cache_delete_pattern(f"product:{product_id}")
        logger.info("Продукт ID=%s успешно удален, кэш продуктов инвалидирован", product_id)
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}") from e
    
    # Возвращаем None для статуса 204 No Content
    return None

@router.post("/check-availability", response_model=Dict[str, bool],dependencies=[Depends(get_current_user)])
async def check_products_availability(
    product_ids: List[int] = Body(..., embed=True),
    session: AsyncSession = Depends(get_session),
):
    """
    Проверяет доступность товаров для заказа.
    
    - **product_ids**: Список ID товаров для проверки
    
    Возвращает словарь, где ключи - это ID товаров, а значения - флаги доступности (True/False)
    """
    try:
        logger.info("Проверка доступности товаров: %s", product_ids)
        result = {}
        
        # Получаем товары из базы данных
        query = select(ProductModel).where(
            ProductModel.id.in_(product_ids)
        )
        products = await session.execute(query)
        products = products.scalars().all()
        
        # Для каждого ID из запроса проверяем, найден ли товар и доступен ли он
        for product_id in product_ids:
            product = next((p for p in products if p.id == product_id), None)
            
            # Товар доступен, если он существует и есть в наличии
            # Проверяем только stock > 0, так как поля is_active может не быть
            is_available = product is not None and product.stock > 0
            
            # Преобразуем product_id в строку для корректной сериализации в JSON
            result[str(product_id)] = is_available
            logger.info("Товар %s: %s", product_id, "доступен" if is_available else "недоступен")
        
        return result
    except Exception as e:
        logger.error("Ошибка при проверке доступности товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла ошибка при проверке доступности товаров: {str(e)}"
        ) from e
