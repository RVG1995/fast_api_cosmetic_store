import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Body, Header,APIRouter
from database import setup_database, get_session, engine
from models import SubCategoryModel,CategoryModel, ProductModel,CountryModel, BrandModel
from auth import require_admin, get_current_user, User
from schema import BrandAddSchema, BrandSchema, BrandUpdateSchema, CategoryAddSchema, CategorySchema, CategoryUpdateSchema, CountryAddSchema, CountrySchema, CountryUpdateSchema, ProductAddSchema,ProductSchema, ProductUpdateSchema, SubCategoryAddSchema, SubCategorySchema, SubCategoryUpdateSchema, PaginatedProductResponse, ProductDetailSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import load_only
import os
import logging
from sqlalchemy import func
import json
from typing import List, Optional, Union, Annotated, Any
from fastapi.staticfiles import StaticFiles
# Импортируем функции для работы с кэшем
from cache import cache_get, cache_set, cache_delete_pattern, invalidate_cache, CACHE_KEYS, CACHE_TTL, close_redis_connection

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_service")

# Создание роутера
router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={404: {"description": "Not found"}},
)

SessionDep = Annotated[AsyncSession,Depends(get_session)]

@router.post("", response_model=ProductSchema, status_code=201)
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
    admin = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"Получен запрос на создание продукта: {name}, цена: {price}")
    logger.info(f"Параметры: description={description}, stock={stock}, category_id={category_id}, subcategory_id={subcategory_id}, country_id={country_id}, brand_id={brand_id}")
    logger.info(f"Изображение: {image and image.filename}")

    # Конвертация строковых значений в нужные типы
    try:
        price_int = int(price)
        stock_int = int(stock)
        category_id_int = int(category_id)
        subcategory_id_int = int(subcategory_id) if subcategory_id else None
        country_id_int = int(country_id)
        brand_id_int = int(brand_id)
    except ValueError as e:
        logger.error(f"Ошибка конвертации типов: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Некорректный формат данных: {str(e)}")

    # Если image равен None, принудительно делаем его None
    if not image:
        image = None
        logger.info("Изображение не предоставлено")

    image_url = None
    if image:
        try:
            logger.info(f"Обработка изображения: {image.filename}")
            extension = os.path.splitext(image.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())
            
            image_url = f"/static/images/{unique_filename}"
            logger.info(f"Изображение сохранено по пути: {image_url}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при сохранении изображения: {str(e)}")

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
        logger.info(f"Продукт успешно создан: ID={product.id}, кэш продуктов инвалидирован")
        
        return product
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        logger.error(f"Ошибка целостности данных: {error_detail}")
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании продукта: {str(e)}")

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
    # Формируем ключ кэша на основе параметров запроса
    cache_key = f"{CACHE_KEYS['products']}list:page={page}:limit={limit}:cat={category_id}:subcat={subcategory_id}:brand={brand_id}:country={country_id}:sort={sort}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о продуктах получены из кэша: page={page}, limit={limit}")
        return cached_data
    
    # Расчет пропуска записей для пагинации
    skip = (page - 1) * limit
    
    # Получаем базовый запрос для доступных продуктов
    query = await ProductModel.get_products_query()
    
    # Добавляем фильтры, если они указаны
    if category_id is not None:
        query = query.filter(ProductModel.category_id == category_id)
    
    if subcategory_id is not None:
        query = query.filter(ProductModel.subcategory_id == subcategory_id)
    
    if brand_id is not None:
        query = query.filter(ProductModel.brand_id == brand_id)
    
    if country_id is not None:
        query = query.filter(ProductModel.country_id == country_id)
    
    # Изменяем сортировку если указана
    if sort == "price_asc":
        # Заменяем сортировку по id на сортировку по цене
        query = query.order_by(None).order_by(ProductModel.price.asc())
    elif sort == "price_desc":
        query = query.order_by(None).order_by(ProductModel.price.desc())
    # В случае sort="newest" или None оставляем сортировку по умолчанию (по id desc)
    
    # Получаем общее количество записей, соответствующих фильтрам
    count_query = select(func.count()).select_from(query.alias())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Применяем пагинацию
    query = query.offset(skip).limit(limit)
    
    # Выполняем запрос
    result = await session.execute(query)
    paginated_products = result.scalars().all()
    
    # Формируем ответ с информацией о пагинации
    response_data = {
        "total": total,
        "limit": limit,
        "offset": skip,
        "items": paginated_products
    }
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, response_data)
    logger.info(f"Данные о продуктах сохранены в кэш: page={page}, limit={limit}, total={total}")
    
    return response_data

@router.get('/admin', response_model=PaginatedProductResponse)
async def get_admin_products(
    session: SessionDep,
    page: int = Query(1, description="Текущая страница пагинации"),
    limit: int = Query(10, description="Количество записей на страницу"),
    category_id: Optional[int] = Query(None, description="ID категории для фильтрации"),
    subcategory_id: Optional[int] = Query(None, description="ID подкатегории для фильтрации"),
    brand_id: Optional[int] = Query(None, description="ID бренда для фильтрации"),
    country_id: Optional[int] = Query(None, description="ID страны для фильтрации"),
    sort: Optional[str] = Query(None, description="Сортировка (newest, price_asc, price_desc)"),
    admin = Depends(require_admin)  # Только администраторы могут использовать этот эндпоинт
):
    # Формируем ключ кэша на основе параметров запроса
    cache_key = f"{CACHE_KEYS['products']}admin:page={page}:limit={limit}:cat={category_id}:subcat={subcategory_id}:brand={brand_id}:country={country_id}:sort={sort}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Админские данные о продуктах получены из кэша: page={page}, limit={limit}")
        return cached_data
    
    # Расчет пропуска записей для пагинации
    skip = (page - 1) * limit
    
    # Получаем базовый запрос для всех продуктов (админский доступ)
    query = await ProductModel.get_admin_products_query()
    
    # Добавляем фильтры, если они указаны
    if category_id is not None:
        query = query.filter(ProductModel.category_id == category_id)
    
    if subcategory_id is not None:
        query = query.filter(ProductModel.subcategory_id == subcategory_id)
    
    if brand_id is not None:
        query = query.filter(ProductModel.brand_id == brand_id)
    
    if country_id is not None:
        query = query.filter(ProductModel.country_id == country_id)
    
    # Изменяем сортировку если указана
    if sort == "price_asc":
        # Заменяем сортировку по id на сортировку по цене
        query = query.order_by(None).order_by(ProductModel.price.asc())
    elif sort == "price_desc":
        query = query.order_by(None).order_by(ProductModel.price.desc())
    # В случае sort="newest" или None оставляем сортировку по умолчанию (по id desc)
    
    # Получаем общее количество записей, соответствующих фильтрам
    count_query = select(func.count()).select_from(query.alias())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Применяем пагинацию
    query = query.offset(skip).limit(limit)
    
    # Выполняем запрос
    result = await session.execute(query)
    paginated_products = result.scalars().all()
    
    # Формируем ответ с информацией о пагинации
    response_data = {
        "total": total,
        "limit": limit,
        "offset": skip,
        "items": paginated_products
    }
    
    # Сохраняем данные в кэш с уменьшенным TTL для админского интерфейса
    # Для админского интерфейса устанавливаем меньшее время жизни кэша, чтобы данные быстрее обновлялись
    await cache_set(cache_key, response_data, CACHE_TTL // 2)
    logger.info(f"Админские данные о продуктах сохранены в кэш: page={page}, limit={limit}, total={total}")
    
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
        logger.info(f"Результаты поиска '{name}' получены из кэша: {len(cached_data)} товаров")
        return cached_data
    
    # Формируем поисковый запрос с использованием LIKE
    search_term = f"%{name}%"
    
    # Создаем запрос к базе данных
    query = select(ProductModel).filter(
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
            "stock": product.stock,  # Может быть полезно для отображения наличия
        }
        
        # Добавляем продукт в список ответа
        response_list.append(product_dict)
    
    # Сохраняем результаты в кэш с меньшим TTL, так как поисковые запросы часто меняются
    await cache_set(cache_key, response_list, CACHE_TTL // 2)
    logger.info(f"Результаты поиска '{name}' сохранены в кэш: {len(response_list)} товаров")
    
    return response_list

@router.get('/{product_id}',response_model = ProductDetailSchema)
async def get_product_id(product_id: int, session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['products']}detail:{product_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о продукте ID={product_id} получены из кэша")
        return cached_data
    
    # Получаем товар
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
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
    
    # Загружаем связанные данные
    try:
        # Загружаем категорию
        if product.category_id:
            category_query = select(CategoryModel).filter(CategoryModel.id == product.category_id)
            category_result = await session.execute(category_query)
            category = category_result.scalars().first()
            if category:
                response_dict["category"] = {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug
                }
        
        # Загружаем подкатегорию
        if product.subcategory_id:
            subcategory_query = select(SubCategoryModel).filter(SubCategoryModel.id == product.subcategory_id)
            subcategory_result = await session.execute(subcategory_query)
            subcategory = subcategory_result.scalars().first()
            if subcategory:
                response_dict["subcategory"] = {
                    "id": subcategory.id,
                    "name": subcategory.name,
                    "slug": subcategory.slug,
                    "category_id": subcategory.category_id
                }
        
        # Загружаем бренд
        if product.brand_id:
            brand_query = select(BrandModel).filter(BrandModel.id == product.brand_id)
            brand_result = await session.execute(brand_query)
            brand = brand_result.scalars().first()
            if brand:
                response_dict["brand"] = {
                    "id": brand.id,
                    "name": brand.name,
                    "slug": brand.slug
                }
        
        # Загружаем страну
        if product.country_id:
            country_query = select(CountryModel).filter(CountryModel.id == product.country_id)
            country_result = await session.execute(country_query)
            country = country_result.scalars().first()
            if country:
                response_dict["country"] = {
                    "id": country.id,
                    "name": country.name,
                    "slug": country.slug
                }
    
    except Exception as e:
        # Логируем ошибку, но продолжаем работу и возвращаем хотя бы базовую информацию о продукте
        print(f"Ошибка при загрузке связанных данных: {str(e)}")
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, response_dict)
    logger.info(f"Данные о продукте ID={product_id} сохранены в кэш")
    
    # Создаем и возвращаем объект схемы из словаря
    return response_dict

@router.put("/{product_id}/form", response_model=ProductSchema)
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
    admin = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    logger.info(f"Получен запрос на обновление продукта ID={product_id}")
    logger.info(f"Параметры: name={name}, price={price}, description={description}, stock={stock}")
    logger.info(f"category_id={category_id}, subcategory_id={subcategory_id}, country_id={country_id}, brand_id={brand_id}")
    logger.info(f"Изображение: {image and image.filename}")
    
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        logger.error(f"Продукт с ID={product_id} не найден")
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
                logger.info(f"subcategory_id установлен в None для продукта ID={product_id}")
            else:
                product.subcategory_id = int(subcategory_id)
                logger.info(f"subcategory_id установлен в {subcategory_id} для продукта ID={product_id}")
                
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
            logger.info(f"Изображение сохранено по пути: {product.image}")
            
        # Сохраняем обновленный продукт
        await session.commit()
        await session.refresh(product)
        
        # Инвалидация кэша продуктов
        await invalidate_cache("products")
        # Инвалидация кэша конкретного продукта
        await cache_delete_pattern(f"{CACHE_KEYS['products']}detail:{product_id}")
        logger.info(f"Продукт ID={product_id} успешно обновлен, кэш продуктов инвалидирован")
        
        return product
        
    except ValueError as e:
        await session.rollback()
        logger.error(f"Ошибка конвертации типов: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Некорректный формат данных: {str(e)}")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        logger.error(f"Ошибка целостности данных: {error_detail}")
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Непредвиденная ошибка при обновлении продукта: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении продукта: {str(e)}")

@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
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
        logger.info(f"Продукт ID={product_id} успешно удален, кэш продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    
    # Возвращаем None для статуса 204 No Content
    return None