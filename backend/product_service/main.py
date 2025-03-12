import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File,Form
from product_service.database import setup_database, get_session, engine
from product_service.models import SubCategoryModel,CategoryModel, ProductModel,CountryModel, BrandModel
from product_service.schema import BrandAddSchema, BrandSchema, BrandUpdateSchema, CategoryAddSchema, CategorySchema, CategoryUpdateSchema, CountryAddSchema, CountrySchema, CountryUpdateSchema, ProductAddSchema,ProductSchema, ProductUpdateSchema, SubCategoryAddSchema, SubCategorySchema, SubCategoryUpdateSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import load_only
import os

from typing import List, Optional,Union,Annotated
from fastapi.staticfiles import StaticFiles

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

@app.post('/products')
async def add_product(
    session: SessionDep,
    name: str = Form(...),
    category_id: int = Form(...),
    country_id: int = Form(...),
    brand_id: int = Form(...),
    subcategory_id: Optional[str] = Form(None),
    price: int = Form(...),
    description: Optional[str] = Form(None),
    stock: int = Form(...),
    uploaded_file: Union[UploadFile, str, None] = File(None) 
):
    # Если uploaded_file равен пустой строке, принудительно делаем его None
    if not uploaded_file or isinstance(uploaded_file, str):
        uploaded_file = None

    image_url = None
    if uploaded_file:        
        extension = os.path.splitext(uploaded_file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(await uploaded_file.read())
        
        image_url = f"/static/images/{unique_filename}"

    if subcategory_id == "" or subcategory_id is None:
        subcategory_id_converted = None
    else:
        subcategory_id_converted = int(subcategory_id)
    
    product_data = ProductAddSchema(
        name=name,
        category_id=category_id,
        country_id=country_id,
        brand_id = brand_id,
        subcategory_id = subcategory_id_converted,
        price=price,
        description=description,
        stock=stock,
        image=image_url
    )
    
    new_product = ProductModel(
        name=product_data.name,
        category_id=product_data.category_id,
        country_id=product_data.country_id,
        brand_id=product_data.brand_id,
        subcategory_id=product_data.subcategory_id,
        price=product_data.price,
        description=product_data.description,
        stock=product_data.stock,
        image=product_data.image
    )
    session.add(new_product)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        error_detail = str(e.orig) if e.orig else str(e)
        raise HTTPException(status_code=400, detail=f"Integrity error: {error_detail}")
    
    return {"ok": "New product was added"}

#@app.get('/products',response_model = List[ProductSchema])
#async def get_categories(session: SessionDep,
  #  limit: int = Query(3 , ge=1, description="Number of items per page"),
   # offset: int = Query(0, ge=0, description="Offset (number of items to skip)")):
   # query = select(ProductModel).limit(limit).offset(offset)
   # result = await session.execute(query)
   # products = result.scalars().all()

    # Получаем общее количество записей
   # count_query = select(func.count(ProductModel.id))
   # count_result = await session.execute(count_query)
   # total = count_result.scalar()

   # return {"total": total, "limit": limit, "offset": offset, "data": products}

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
    session: SessionDep
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

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    session: SessionDep
):
    # Ищем продукт по id
    query = select(ProductModel).filter(ProductModel.id == product_id)
    result = await session.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Удаляем продукт
    try:
        session.delete(product)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8001, reload=True)