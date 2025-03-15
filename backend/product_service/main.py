import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Body, Header
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который должен выполниться при запуске приложения (startup)
    await setup_database()  # вызываем асинхронную функцию для создания таблиц или миграций
    logger.info("База данных сервиса продуктов инициализирована")
    yield  # здесь приложение будет работать
    # Код для завершения работы приложения (shutdown) можно добавить после yield, если нужно
    logger.info("Завершение работы сервиса продуктов")
    await close_redis_connection()
    await engine.dispose()  # корректное закрытие соединений с базой данных
    logger.info("Соединения с БД и Redis закрыты")

app = FastAPI(lifespan=lifespan)

UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
# Настройка CORS
origins = [
    "http://localhost:3000",  # адрес вашего фронтенда
    # можно добавить другие источники, если нужно
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Разрешенные источники
    allow_credentials=True,
    allow_methods=["*"],        # Разрешенные методы (GET, POST и т.д.)
    allow_headers=["*"],        # Разрешенные заголовки
)

SessionDep = Annotated[AsyncSession,Depends(get_session)]

@app.post("/products", response_model=ProductSchema, status_code=201)
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

@app.get('/products', response_model=PaginatedProductResponse)
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

@app.get('/admin/products', response_model=PaginatedProductResponse)
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

@app.get('/products/search', response_model=List[dict])
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

@app.get('/products/{product_id}',response_model = ProductDetailSchema)
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

@app.put("/products/{product_id}/form", response_model=ProductSchema)
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

@app.delete("/products/{product_id}", status_code=204)
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

@app.get('/categories',response_model = List[CategorySchema])
async def get_categories(session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['categories']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о категориях получены из кэша: {len(cached_data)} записей")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(CategoryModel)
    result = await session.execute(query)
    categories = result.scalars().all()
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, categories)
    logger.info(f"Данные о категориях сохранены в кэш: {len(categories)} записей")
    
    return categories

@app.post('/categories',response_model = CategorySchema)
async def add_categories(
    data: CategoryAddSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Проверка уникальности slug
    slug_query = select(CategoryModel).filter(CategoryModel.slug == data.slug)
    result = await session.execute(slug_query)
    existing_category = result.scalars().first()
    
    if existing_category:
        raise HTTPException(status_code=400, detail=f"Категория с slug '{data.slug}' уже существует")
    
    new_category = CategoryModel(
        name = data.name,
        slug= data.slug,
    )
    session.add(new_category)
    try:
        await session.commit()
        # Инвалидация кэша при добавлении новой категории
        await invalidate_cache("categories")
        logger.info(f"Добавлена новая категория '{data.name}', кэш категорий инвалидирован")
    except IntegrityError as e:
        # Откатываем транзакцию, если произошла ошибка
        await session.rollback()
        # Можно извлечь оригинальное сообщение об ошибке для более подробного описания:
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return new_category

@app.put("/categories/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: int,
    update_data: CategoryUpdateSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем категорию по id
    query = select(CategoryModel).filter(CategoryModel.id == category_id)
    result = await session.execute(query)
    category = result.scalars().first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Проверка уникальности slug при обновлении, если он был изменен
    if update_data.slug is not None and update_data.slug != category.slug:
        slug_query = select(CategoryModel).filter(
            CategoryModel.slug == update_data.slug,
            CategoryModel.id != category_id  # Исключаем текущую категорию из проверки
        )
        result = await session.execute(slug_query)
        existing_category = result.scalars().first()
        
        if existing_category:
            raise HTTPException(status_code=400, detail=f"Категория с slug '{update_data.slug}' уже существует")

    # Обновляем поля категории, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(category, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(category)
        
        # Инвалидация кэша при обновлении категории
        await invalidate_cache("categories")
        # Также инвалидируем кэш продуктов, так как категории связаны с продуктами
        await invalidate_cache("products")
        logger.info(f"Обновлена категория ID={category_id}, кэш категорий и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")

    return category

@app.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем категорию по id
    query = select(CategoryModel).filter(CategoryModel.id == category_id)
    result = await session.execute(query)
    category = result.scalars().first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Удаляем категорию
    try:
        await session.delete(category)
        await session.commit()
        
        # Инвалидация кэша при удалении категории
        await invalidate_cache("categories")
        # Также инвалидируем кэш продуктов
        await invalidate_cache("products")
        logger.info(f"Удалена категория ID={category_id}, кэш категорий и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(
            status_code=400, 
            detail=f"Невозможно удалить категорию, так как она используется в других объектах. Ошибка: {error_detail}"
        )
    
    # Возвращаем None для статуса 204 No Content
    return None

@app.get('/countries',response_model = List[CountrySchema])
async def get_countries(session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['countries']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о странах получены из кэша: {len(cached_data)} записей")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(CountryModel)
    result = await session.execute(query)
    countries = result.scalars().all()
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, countries)
    logger.info(f"Данные о странах сохранены в кэш: {len(countries)} записей")
    
    return countries

@app.post('/countries',response_model = CountrySchema)
async def add_countries(
    data: CountryAddSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Проверка уникальности slug
    slug_query = select(CountryModel).filter(CountryModel.slug == data.slug)
    result = await session.execute(slug_query)
    existing_country = result.scalars().first()
    
    if existing_country:
        raise HTTPException(status_code=400, detail=f"Страна с slug '{data.slug}' уже существует")
    
    new_country = CountryModel(
        name = data.name,
        slug= data.slug,
    )
    session.add(new_country)
    try:
        await session.commit()
        
        # Инвалидация кэша стран
        await invalidate_cache("countries")
        # Инвалидация кэша продуктов, так как они связаны со странами
        await invalidate_cache("products")
        logger.info(f"Добавлена новая страна '{data.name}', кэш стран и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return new_country

@app.put("/countries/{country_id}", response_model=CountrySchema)
async def update_country(
    country_id: int,
    update_data: CountryUpdateSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем страну по id
    query = select(CountryModel).filter(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    # Проверка уникальности slug при обновлении, если он был изменен
    if update_data.slug is not None and update_data.slug != country.slug:
        slug_query = select(CountryModel).filter(
            CountryModel.slug == update_data.slug,
            CountryModel.id != country_id  # Исключаем текущую страну из проверки
        )
        result = await session.execute(slug_query)
        existing_country = result.scalars().first()
        
        if existing_country:
            raise HTTPException(status_code=400, detail=f"Страна с slug '{update_data.slug}' уже существует")

    # Обновляем поля страны, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(country, field, value)
    
    try:
        await session.commit()
        await session.refresh(country)
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")

    return country

@app.get('/countries/{country_id}',response_model = CountrySchema)
async def get_country_id(country_id: int, session: SessionDep):
    query = select(CountryModel).filter(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    if not country:
        raise HTTPException(status_code=404, detail="Category not found")
    return country

@app.delete("/countries/{country_id}", status_code=204)
async def delete_country(
    country_id: int,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем страну по id
    query = select(CountryModel).filter(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    # Удаляем страну
    try:
        await session.delete(country)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(
            status_code=400, 
            detail=f"Невозможно удалить страну, так как она используется в других объектах. Ошибка: {error_detail}"
        )
    
    # Возвращаем None для статуса 204 No Content
    return None

@app.get('/brands',response_model = List[BrandSchema])
async def get_brands(session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['brands']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о брендах получены из кэша: {len(cached_data)} записей")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(BrandModel)
    result = await session.execute(query)
    brands = result.scalars().all()
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, brands)
    logger.info(f"Данные о брендах сохранены в кэш: {len(brands)} записей")
    
    return brands

@app.post('/brands',response_model = BrandSchema)
async def add_brands(
    data: BrandAddSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Проверка уникальности slug
    slug_query = select(BrandModel).filter(BrandModel.slug == data.slug)
    result = await session.execute(slug_query)
    existing_brand = result.scalars().first()
    
    if existing_brand:
        raise HTTPException(status_code=400, detail=f"Бренд с slug '{data.slug}' уже существует")
    
    new_brand = BrandModel(
        name = data.name,
        slug= data.slug,
    )
    session.add(new_brand)
    try:
        await session.commit()
        
        # Инвалидация кэша брендов
        await invalidate_cache("brands")
        # Инвалидация кэша продуктов, так как они связаны с брендами
        await invalidate_cache("products")
        logger.info(f"Добавлен новый бренд '{data.name}', кэш брендов и продуктов инвалидирован")
    except IntegrityError as e:
        # Откатываем транзакцию, если произошла ошибка
        await session.rollback()
        # Можно извлечь оригинальное сообщение об ошибке для более подробного описания:
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return new_brand

@app.put("/brands/{brand_id}", response_model=BrandSchema)
async def update_brand(
    brand_id: int,
    update_data: BrandUpdateSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем бренд по id
    query = select(BrandModel).filter(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Проверка уникальности slug при обновлении, если он был изменен
    if update_data.slug is not None and update_data.slug != brand.slug:
        slug_query = select(BrandModel).filter(
            BrandModel.slug == update_data.slug,
            BrandModel.id != brand_id  # Исключаем текущий бренд из проверки
        )
        result = await session.execute(slug_query)
        existing_brand = result.scalars().first()
        
        if existing_brand:
            raise HTTPException(status_code=400, detail=f"Бренд с slug '{update_data.slug}' уже существует")

    # Обновляем поля бренда, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(brand, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(brand)
        
        # Инвалидация кэша брендов
        await invalidate_cache("brands")
        # Инвалидация кэша продуктов, так как они связаны с брендами
        await invalidate_cache("products")
        logger.info(f"Обновлен бренд ID={brand_id}, кэш брендов и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")

    return brand

@app.get('/brands/{brand_id}',response_model = BrandSchema)
async def get_brand_id(brand_id: int, session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['brands']}{brand_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о бренде ID={brand_id} получены из кэша")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(BrandModel).filter(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, brand)
    logger.info(f"Данные о бренде ID={brand_id} сохранены в кэш")
    
    return brand

@app.delete("/brands/{brand_id}", status_code=204)
async def delete_brand(
    brand_id: int,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем бренд по id
    query = select(BrandModel).filter(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Удаляем бренд
    try:
        await session.delete(brand)
        await session.commit()
        
        # Инвалидация кэша брендов
        await invalidate_cache("brands")
        # Инвалидация кэша продуктов, так как они связаны с брендами
        await invalidate_cache("products")
        logger.info(f"Удален бренд ID={brand_id}, кэш брендов и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(
            status_code=400, 
            detail=f"Невозможно удалить бренд, так как он используется в других объектах. Ошибка: {error_detail}"
        )
    
    # Возвращаем None для статуса 204 No Content
    return None

@app.get('/subcategories',response_model = List[SubCategorySchema])
async def get_subcategories(session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['subcategories']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о подкатегориях получены из кэша: {len(cached_data)} записей")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(SubCategoryModel)
    result = await session.execute(query)
    subcategories = result.scalars().all()
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, subcategories)
    logger.info(f"Данные о подкатегориях сохранены в кэш: {len(subcategories)} записей")
    
    return subcategories

@app.post('/subcategories',response_model = SubCategorySchema)
async def add_subcategories(
    data: SubCategoryAddSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Проверка уникальности slug
    slug_query = select(SubCategoryModel).filter(SubCategoryModel.slug == data.slug)
    result = await session.execute(slug_query)
    existing_subcategory = result.scalars().first()
    
    if existing_subcategory:
        raise HTTPException(status_code=400, detail=f"Подкатегория с slug '{data.slug}' уже существует")
    
    new_sub_category = SubCategoryModel(
        name = data.name,
        slug = data.slug,
        category_id = data.category_id,
    )
    session.add(new_sub_category)
    try:
        await session.commit()
        
        # Инвалидация кэша подкатегорий
        await invalidate_cache("subcategories")
        # Инвалидация кэша продуктов, так как они связаны с подкатегориями
        await invalidate_cache("products")
        logger.info(f"Добавлена новая подкатегория '{data.name}', кэш подкатегорий и продуктов инвалидирован")
    except IntegrityError as e:
        # Откатываем транзакцию, если произошла ошибка
        await session.rollback()
        # Можно извлечь оригинальное сообщение об ошибке для более подробного описания:
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return new_sub_category

@app.put("/subcategories/{subcategory_id}", response_model=SubCategorySchema)
async def update_subcategory(
    subcategory_id: int,
    update_data: SubCategoryUpdateSchema,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем подкатегорию по id
    query = select(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    # Проверка уникальности slug при обновлении, если он был изменен
    if update_data.slug is not None and update_data.slug != subcategory.slug:
        slug_query = select(SubCategoryModel).filter(
            SubCategoryModel.slug == update_data.slug,
            SubCategoryModel.id != subcategory_id  # Исключаем текущую подкатегорию из проверки
        )
        result = await session.execute(slug_query)
        existing_subcategory = result.scalars().first()
        
        if existing_subcategory:
            raise HTTPException(status_code=400, detail=f"Подкатегория с slug '{update_data.slug}' уже существует")

    # Обновляем поля подкатегории, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(subcategory, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(subcategory)
        
        # Инвалидация кэша подкатегорий
        await invalidate_cache("subcategories")
        # Инвалидация кэша продуктов, так как они связаны с подкатегориями
        await invalidate_cache("products")
        logger.info(f"Обновлена подкатегория ID={subcategory_id}, кэш подкатегорий и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return subcategory

@app.get('/subcategories/{subcategory_id}',response_model = SubCategorySchema)
async def get_subcategory_id(subcategory_id: int, session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['subcategories']}{subcategory_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о подкатегории ID={subcategory_id} получены из кэша")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, subcategory)
    logger.info(f"Данные о подкатегории ID={subcategory_id} сохранены в кэш")
    
    return subcategory

@app.delete("/subcategories/{subcategory_id}", status_code=204)
async def delete_subcategory(
    subcategory_id: int,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin)
):
    # Ищем подкатегорию по id
    query = select(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    # Удаляем подкатегорию
    try:
        await session.delete(subcategory)
        await session.commit()
        
        # Инвалидация кэша подкатегорий
        await invalidate_cache("subcategories")
        # Инвалидация кэша продуктов, так как они связаны с подкатегориями
        await invalidate_cache("products")
        logger.info(f"Удалена подкатегория ID={subcategory_id}, кэш подкатегорий и продуктов инвалидирован")
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(
            status_code=400, 
            detail=f"Невозможно удалить подкатегорию, так как она используется в других объектах. Ошибка: {error_detail}"
        )
    
    # Возвращаем None для статуса 204 No Content
    return None

@app.get('/auth-check')
async def check_auth(user = Depends(get_current_user)):
    """Эндпоинт для проверки авторизации и отладки токена JWT"""
    if user:
        return {
            "authenticated": True,
            "user_id": user.id,
            "is_admin": user.is_admin,
            "is_super_admin": user.is_super_admin,
            "is_active": user.is_active
        }
    else:
        return {
            "authenticated": False,
            "message": "Пользователь не авторизован"
        }

@app.post('/products/batch', tags=["Products"])
async def get_products_batch(
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Получить информацию о нескольких продуктах по их ID.
    Возвращает список объектов продуктов для всех найденных ID.
    Требуются права администратора.
    """
    logger.info(f"Пакетный запрос информации о продуктах: {product_ids}")
    
    # Проверка прав администратора
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_super_admin', False):
        logger.warning(f"Пользователь {current_user.id} пытался получить пакетный доступ к продуктам без прав администратора")
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
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

@app.post('/products/public-batch', tags=["Products"])
async def get_products_public_batch(
    product_ids: List[int] = Body(..., embed=True, description="Список ID продуктов"),
    service_key: str = Header(..., alias="Service-Key", description="Секретный ключ для доступа к API"),
    session: AsyncSession = Depends(get_session)
):
    """
    Публичный API для получения информации о нескольких продуктах по их ID.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_ids**: Список ID продуктов
    - **service_key**: Секретный ключ для доступа к API (передается в заголовке)
    """
    # Проверяем секретный ключ (должен совпадать с ключом в конфигурации)
    INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "your-internal-service-key")
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

@app.get('/categories/{category_id}',response_model = CategorySchema)
async def get_category_id(category_id: int, session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['categories']}{category_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные о категории ID={category_id} получены из кэша")
        return cached_data
    
    # Если данных в кэше нет, получаем их из базы
    query = select(CategoryModel).filter(CategoryModel.id == category_id)
    result = await session.execute(query)
    category = result.scalars().first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Сохраняем данные в кэш
    await cache_set(cache_key, category)
    logger.info(f"Данные о категории ID={category_id} сохранены в кэш")
    
    return category

@app.put("/products/{product_id}/stock", status_code=200)
async def update_product_stock(
    product_id: int,
    data: dict = Body(..., description="Данные для обновления остатка"),
    admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
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
        logger.info(f"Обновлено количество товара ID={product_id}: {old_stock} -> {new_stock} администратором {admin.get('user_id')}")
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при обновлении количества товара: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}")

@app.put("/products/{product_id}/public-stock", status_code=200)
async def update_product_public_stock(
    product_id: int,
    data: dict = Body(..., description="Данные для обновления остатка"),
    service_key: str = Header(..., alias="Service-Key", description="Секретный ключ для доступа к API"),
    session: AsyncSession = Depends(get_session)
):
    """
    Публичный API для обновления количества товара на складе.
    Доступен только для внутренних сервисов с правильным ключом.
    
    - **product_id**: ID продукта
    - **data**: Данные для обновления (должны содержать поле 'stock')
    - **service_key**: Секретный ключ для доступа к API (передается в заголовке)
    """
    # Проверяем секретный ключ (должен совпадать с ключом в конфигурации)
    INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "your-internal-service-key")
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
        logger.info(f"Публичное обновление количества товара ID={product_id}: {old_stock} -> {new_stock} через сервисный ключ")
        
        return {"id": product.id, "stock": product.stock}
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при публичном обновлении количества товара: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества товара: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8001, reload=True)