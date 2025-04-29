"""Модуль для проверки тестовых данных в базе данных.

Выводит информацию о категориях, подкатегориях, брендах, странах и продуктах.
"""

import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import CategoryModel, ProductModel, BrandModel, CountryModel, SubCategoryModel
from database import DATABASE_URL

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_data():
    """Проверяет и выводит данные из базы данных.

    Выполняет запросы к базе данных и выводит информацию о:
    - Категориях
    - Подкатегориях
    - Брендах
    - Странах
    - Продуктах (первые 5)
    """
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Проверяем категории
        categories_query = select(CategoryModel)
        categories_result = await session.execute(categories_query)
        categories = categories_result.scalars().all()
        logger.info('Категории (%d):', len(categories))
        for category in categories:
            logger.info('  - %s', category.name)
        
        # Проверяем подкатегории
        subcategories_query = select(SubCategoryModel)
        subcategories_result = await session.execute(subcategories_query)
        subcategories = subcategories_result.scalars().all()
        logger.info('\nПодкатегории (%d):', len(subcategories))
        for subcategory in subcategories:
            logger.info('  - %s (Категория: %s)', subcategory.name, subcategory.category_id)
        
        # Проверяем бренды
        brands_query = select(BrandModel)
        brands_result = await session.execute(brands_query)
        brands = brands_result.scalars().all()
        logger.info('\nБренды (%d):', len(brands))
        for brand in brands:
            logger.info('  - %s', brand.name)
        
        # Проверяем страны
        countries_query = select(CountryModel)
        countries_result = await session.execute(countries_query)
        countries = countries_result.scalars().all()
        logger.info('\nСтраны (%d):', len(countries))
        for country in countries:
            logger.info('  - %s', country.name)
        
        # Проверяем продукты
        products_query = select(ProductModel)
        products_result = await session.execute(products_query)
        products = products_result.scalars().all()
        logger.info('\nПродукты (%d):', len(products))
        for product in products[:5]:  # Выводим только первые 5 продуктов
            logger.info('  - %s (Цена: %s, Количество: %s)', product.name, product.price, product.stock)
            logger.info('    Категория: %s, Бренд: %s, Страна: %s', product.category_id, product.brand_id, product.country_id)
            logger.info('    Подкатегория: %s', product.subcategory_id)
        
        if len(products) > 5:
            logger.info('  ... и еще %d продуктов', len(products) - 5)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_data())
