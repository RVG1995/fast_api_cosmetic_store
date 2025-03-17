import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import CategoryModel, ProductModel, BrandModel, CountryModel, SubCategoryModel
from database import DATABASE_URL

async def check_data():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Проверяем категории
        categories_query = select(CategoryModel)
        categories_result = await session.execute(categories_query)
        categories = categories_result.scalars().all()
        print(f'Категории ({len(categories)}):')
        for category in categories:
            print(f'  - {category.name}')
        
        # Проверяем подкатегории
        subcategories_query = select(SubCategoryModel)
        subcategories_result = await session.execute(subcategories_query)
        subcategories = subcategories_result.scalars().all()
        print(f'\nПодкатегории ({len(subcategories)}):')
        for subcategory in subcategories:
            print(f'  - {subcategory.name} (Категория: {subcategory.category_id})')
        
        # Проверяем бренды
        brands_query = select(BrandModel)
        brands_result = await session.execute(brands_query)
        brands = brands_result.scalars().all()
        print(f'\nБренды ({len(brands)}):')
        for brand in brands:
            print(f'  - {brand.name}')
        
        # Проверяем страны
        countries_query = select(CountryModel)
        countries_result = await session.execute(countries_query)
        countries = countries_result.scalars().all()
        print(f'\nСтраны ({len(countries)}):')
        for country in countries:
            print(f'  - {country.name}')
        
        # Проверяем продукты
        products_query = select(ProductModel)
        products_result = await session.execute(products_query)
        products = products_result.scalars().all()
        print(f'\nПродукты ({len(products)}):')
        for i, product in enumerate(products[:5]):  # Выводим только первые 5 продуктов
            print(f'  - {product.name} (Цена: {product.price}, Количество: {product.stock})')
            print(f'    Категория: {product.category_id}, Бренд: {product.brand_id}, Страна: {product.country_id}')
            print(f'    Подкатегория: {product.subcategory_id}')
        
        if len(products) > 5:
            print(f'  ... и еще {len(products) - 5} продуктов')
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_data()) 