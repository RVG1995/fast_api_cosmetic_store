import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Body
from database import setup_database, get_session, engine
from models import SubCategoryModel,CategoryModel, ProductModel,CountryModel, BrandModel
from auth import require_admin, get_current_user
from schema import BrandAddSchema, BrandSchema, BrandUpdateSchema, CategoryAddSchema, CategorySchema, CategoryUpdateSchema, CountryAddSchema, CountrySchema, CountryUpdateSchema, ProductAddSchema,ProductSchema, ProductUpdateSchema, SubCategoryAddSchema, SubCategorySchema, SubCategoryUpdateSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import load_only
import os
import logging

from typing import List, Optional,Union,Annotated
from fastapi.staticfiles import StaticFiles

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который должен выполниться при запуске приложения (startup)
    await setup_database()  # вызываем асинхронную функцию для создания таблиц или миграций
    yield  # здесь приложение будет работать
    # Код для завершения работы приложения (shutdown) можно добавить после yield, если нужно
    await engine.dispose()  # корректное закрытие соединений с базой данных

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
        price_float = float(price)
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
            price=price_float,
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
        logger.info(f"Продукт успешно создан: ID={product.id}")
        return product
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        logger.error(f"Ошибка целостности данных: {error_detail}")
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании продукта: {str(e)}")


@app.get('/products',response_model = List[ProductSchema])
async def get_products(session: SessionDep):
    query = select(ProductModel).options(
        load_only(
            ProductModel.name,
            ProductModel.category_id,
            ProductModel.country_id,
            ProductModel.brand_id,
            ProductModel.subcategory_id,
            ProductModel.price,
            ProductModel.description,
            ProductModel.stock,
            ProductModel.image
        )
    )
    result = await session.execute(query)
    return result.scalars().all()

@app.get('/products/{product_id}',response_model = ProductSchema)
async def get_product_id(product_id: int, session: SessionDep):
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int,
    update_data: ProductUpdateSchema,
    admin = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновляем поля продукта, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(product, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(product)
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")

    return product

# Новый эндпоинт для обновления с поддержкой загрузки файлов
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

    # Конвертация строковых значений в нужные типы
    price_float = None
    stock_int = None
    category_id_int = None
    subcategory_id_int = None
    country_id_int = None
    brand_id_int = None
    
    try:
        if price is not None:
            price_float = float(price)
        if stock is not None:
            stock_int = int(stock)
        if category_id is not None:
            category_id_int = int(category_id)
        if subcategory_id is not None:
            subcategory_id_int = int(subcategory_id)
        if country_id is not None:
            country_id_int = int(country_id)
        if brand_id is not None:
            brand_id_int = int(brand_id)
    except ValueError as e:
        logger.error(f"Ошибка конвертации типов: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Некорректный формат данных: {str(e)}")

    # Если изображение предоставлено, обрабатываем его
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
    
    # Создаем словарь только с предоставленными значениями
    update_fields = {}
    if name is not None:
        update_fields["name"] = name
    if price_float is not None:
        update_fields["price"] = price_float
    if description is not None:
        update_fields["description"] = description
    if stock_int is not None:
        update_fields["stock"] = stock_int
    if category_id_int is not None:
        update_fields["category_id"] = category_id_int
    if subcategory_id_int is not None:
        update_fields["subcategory_id"] = subcategory_id_int
    if country_id_int is not None:
        update_fields["country_id"] = country_id_int
    if brand_id_int is not None:
        update_fields["brand_id"] = brand_id_int
    if image_url is not None:
        update_fields["image"] = image_url

    logger.info(f"Обновляемые поля: {update_fields}")

    # Обновляем поля продукта
    for field, value in update_fields.items():
        setattr(product, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(product)
        logger.info(f"Продукт ID={product_id} успешно обновлен")
        return product
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        logger.error(f"Ошибка целостности данных: {error_detail}")
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении продукта: {str(e)}")

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    admin = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
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
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    
    # Возвращаем None для статуса 204 No Content
    return None

@app.get('/categories',response_model = List[CategorySchema])
async def get_categories(session: SessionDep):
    query = select(CategoryModel)
    result = await session.execute(query)
    return result.scalars().all()

@app.post('/categories',response_model = CategorySchema)
async def add_categories(data: CategoryAddSchema, session: SessionDep):
    new_category = CategoryModel(
        name = data.name,
        slug= data.slug,
    )
    session.add(new_category)
    try:
        await session.commit()
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
    session: SessionDep
):
    # Ищем продукт по id
    query = select(CategoryModel).filter(CategoryModel.id == category_id)
    result = await session.execute(query)
    category = result.scalars().first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновляем поля продукта, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(category, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(category)
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")

    return category

@app.get('/categories/{category_id}',response_model = CategorySchema)
async def get_category_id(category_id: int, session: SessionDep):
    query = select(CategoryModel).filter(CategoryModel.id == category_id)
    result = await session.execute(query)
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@app.get('/countries',response_model = List[CountrySchema])
async def get_countries(session: SessionDep):
    query = select(CountryModel)
    result = await session.execute(query)
    return result.scalars().all()

@app.post('/countries',response_model = CountrySchema)
async def add_countries(data: CountryAddSchema, session: SessionDep):
    new_country = CountryModel(
        name = data.name,
        slug= data.slug,
    )
    session.add(new_country)
    try:
        await session.commit()
    except IntegrityError as e:
        # Откатываем транзакцию, если произошла ошибка
        await session.rollback()
        # Можно извлечь оригинальное сообщение об ошибке для более подробного описания:
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return new_country

@app.put("/countries/{country_id}", response_model=CountrySchema)
async def update_category(
    country_id: int,
    update_data: CountryUpdateSchema,
    session: SessionDep
):
    # Ищем продукт по id
    query = select(CountryModel).filter(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    
    if not country:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновляем поля продукта, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(country, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
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

@app.get('/brands',response_model = List[BrandSchema])
async def get_brands(session: SessionDep):
    query = select(BrandModel)
    result = await session.execute(query)
    return result.scalars().all()

@app.post('/brands',response_model = BrandSchema)
async def add_brands(data: BrandAddSchema, session: SessionDep):
    new_brand = BrandModel(
        name = data.name,
        slug= data.slug,
    )
    session.add(new_brand)
    try:
        await session.commit()
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
    session: SessionDep
):
    # Ищем продукт по id
    query = select(BrandModel).filter(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновляем поля продукта, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(brand, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(brand)
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")

    return brand

@app.get('/brands/{brand_id}',response_model = BrandSchema)
async def get_brand_id(brand_id: int, session: SessionDep):
    query = select(BrandModel).filter(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Category not found")
    return brand


@app.get('/subcategories',response_model = List[SubCategorySchema])
async def get_subcategories(session: SessionDep):
    query = select(SubCategoryModel)
    result = await session.execute(query)
    return result.scalars().all()

@app.post('/subcategories',response_model = SubCategorySchema)
async def add_subcategories(data: SubCategoryAddSchema, session: SessionDep):
    new_sub_category = SubCategoryModel(
        name = data.name,
        slug = data.slug,
        category_id = data.category_id,
    )
    session.add(new_sub_category)
    try:
        await session.commit()
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
    session: SessionDep
):
    # Ищем продукт по id
    query = select(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновляем поля продукта, используя только переданные данные
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(subcategory, field, value)
    
    try:
        await session.commit()
        # Обновляем объект из базы, чтобы вернуть актуальные данные
        await session.refresh(subcategory)
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    return subcategory

@app.get('/subcategories/{subcategory_id}',response_model = SubCategorySchema)
async def get_subcategory_id(subcategory_id: int, session: SessionDep):
    query = select(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    if not subcategory:
        raise HTTPException(status_code=404, detail="Category not found")
    return subcategory

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8001, reload=True)