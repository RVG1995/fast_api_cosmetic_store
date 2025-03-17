import asyncio
import logging
import random
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import os
from dotenv import load_dotenv

from models import CategoryModel, SubCategoryModel, BrandModel, CountryModel, ProductModel, Base
from database import DATABASE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_test_data")

# Загрузка переменных окружения
load_dotenv()

# Создание подключения к базе данных
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Тестовые данные
CATEGORIES = [
    {"name": "Уход за лицом", "slug": "face-care"},
    {"name": "Уход за телом", "slug": "body-care"}
]

SUBCATEGORIES = [
    {"name": "Крема для лица", "slug": "face-creams", "category_id": 1},
    {"name": "Лосьоны для тела", "slug": "body-lotions", "category_id": 2}
]

BRANDS = [
    {"name": "NaturalBeauty", "slug": "natural-beauty"},
    {"name": "PureGlow", "slug": "pure-glow"}
]

COUNTRIES = [
    {"name": "Франция", "slug": "france"},
    {"name": "Корея", "slug": "korea"}
]

PRODUCT_NAMES = [
    "Крем для лица увлажняющий",
    "Лосьон для тела с алоэ вера",
    "Антивозрастная сыворотка",
    "Гель для душа с экстрактом лаванды",
    "Маска для лица с глиной",
    "Крем для рук питательный",
    "Тоник для лица с витамином С",
    "Масло для тела восстанавливающее",
    "Скраб для лица с фруктовыми кислотами",
    "Крем для ног освежающий",
    "Пенка для умывания с экстрактом зеленого чая",
    "Бальзам для губ защитный",
    "Крем от морщин вокруг глаз",
    "Молочко для тела питательное",
    "Сыворотка с гиалуроновой кислотой",
    "Масло для волос питательное",
    "Крем-маска ночная восстанавливающая",
    "Гель для лица охлаждающий",
    "Мицеллярная вода очищающая",
    "Спрей для тела тонизирующий"
]

PRODUCT_DESCRIPTIONS = [
    "Этот продукт обеспечивает глубокое увлажнение и питание кожи.",
    "Содержит натуральные компоненты, которые бережно ухаживают за вашей кожей.",
    "Помогает бороться с признаками старения и улучшает тон кожи.",
    "Придает коже сияние и здоровый вид.",
    "Защищает от негативного воздействия окружающей среды.",
    "Восстанавливает поврежденные участки и укрепляет естественный барьер кожи.",
    "Подходит для ежедневного использования.",
    "Клинически протестировано дерматологами.",
    "Не содержит парабенов и искусственных красителей.",
    "Подходит для чувствительной кожи."
]

async def create_categories():
    """Создание категорий"""
    async with async_session() as session:
        # Проверяем, есть ли уже категории в БД
        query = select(CategoryModel)
        result = await session.execute(query)
        existing_categories = result.scalars().all()
        
        if existing_categories:
            logger.info(f"В базе данных уже есть {len(existing_categories)} категорий")
            return
        
        # Создаем категории
        for category_data in CATEGORIES:
            category = CategoryModel(**category_data)
            session.add(category)
        
        await session.commit()
        logger.info(f"Добавлено {len(CATEGORIES)} категорий")

async def create_subcategories():
    """Создание подкатегорий"""
    async with async_session() as session:
        # Проверяем, есть ли уже подкатегории в БД
        query = select(SubCategoryModel)
        result = await session.execute(query)
        existing_subcategories = result.scalars().all()
        
        if existing_subcategories:
            logger.info(f"В базе данных уже есть {len(existing_subcategories)} подкатегорий")
            return
        
        # Создаем подкатегории
        for subcategory_data in SUBCATEGORIES:
            subcategory = SubCategoryModel(**subcategory_data)
            session.add(subcategory)
        
        await session.commit()
        logger.info(f"Добавлено {len(SUBCATEGORIES)} подкатегорий")

async def create_brands():
    """Создание брендов"""
    async with async_session() as session:
        # Проверяем, есть ли уже бренды в БД
        query = select(BrandModel)
        result = await session.execute(query)
        existing_brands = result.scalars().all()
        
        if existing_brands:
            logger.info(f"В базе данных уже есть {len(existing_brands)} брендов")
            return
        
        # Создаем бренды
        for brand_data in BRANDS:
            brand = BrandModel(**brand_data)
            session.add(brand)
        
        await session.commit()
        logger.info(f"Добавлено {len(BRANDS)} брендов")

async def create_countries():
    """Создание стран"""
    async with async_session() as session:
        # Проверяем, есть ли уже страны в БД
        query = select(CountryModel)
        result = await session.execute(query)
        existing_countries = result.scalars().all()
        
        if existing_countries:
            logger.info(f"В базе данных уже есть {len(existing_countries)} стран")
            return
        
        # Создаем страны
        for country_data in COUNTRIES:
            country = CountryModel(**country_data)
            session.add(country)
        
        await session.commit()
        logger.info(f"Добавлено {len(COUNTRIES)} стран")

async def create_products(count: int = 20):
    """Создание продуктов"""
    async with async_session() as session:
        # Проверяем, есть ли уже продукты в БД
        query = select(ProductModel)
        result = await session.execute(query)
        existing_products = result.scalars().all()
        
        if existing_products:
            logger.info(f"В базе данных уже есть {len(existing_products)} продуктов")
            return
        
        # Получаем существующие категории, подкатегории, бренды и страны
        categories_query = select(CategoryModel)
        categories_result = await session.execute(categories_query)
        categories = categories_result.scalars().all()
        
        subcategories_query = select(SubCategoryModel)
        subcategories_result = await session.execute(subcategories_query)
        subcategories = subcategories_result.scalars().all()
        
        brands_query = select(BrandModel)
        brands_result = await session.execute(brands_query)
        brands = brands_result.scalars().all()
        
        countries_query = select(CountryModel)
        countries_result = await session.execute(countries_query)
        countries = countries_result.scalars().all()
        
        if not categories or not brands or not countries:
            logger.error("Необходимо сначала создать категории, бренды и страны")
            return
        
        # Создаем продукты
        for i in range(count):
            name = PRODUCT_NAMES[i % len(PRODUCT_NAMES)]
            description = random.choice(PRODUCT_DESCRIPTIONS)
            price = round(random.uniform(100, 5000), 2)
            stock = random.randint(0, 100)
            category = random.choice(categories)
            brand = random.choice(brands)
            country = random.choice(countries)
            
            # Случайно выбираем, будет ли у продукта подкатегория
            subcategory_id = None
            if random.choice([True, False]) and subcategories:
                # Выбираем подкатегорию, связанную с выбранной категорией
                matching_subcategories = [sc for sc in subcategories if sc.category_id == category.id]
                if matching_subcategories:
                    subcategory = random.choice(matching_subcategories)
                    subcategory_id = subcategory.id
            
            product = ProductModel(
                name=f"{name} {i+1}",
                description=description,
                price=price,
                stock=stock,
                category_id=category.id,
                brand_id=brand.id,
                country_id=country.id,
                subcategory_id=subcategory_id,
                image=f"/static/images/product_{i+1}.jpg"
            )
            
            session.add(product)
        
        await session.commit()
        logger.info(f"Добавлено {count} продуктов")

async def main():
    try:
        # Создаем категории, подкатегории, бренды, страны и продукты
        await create_categories()
        await create_subcategories()
        await create_brands()
        await create_countries()
        await create_products(20)
        
        logger.info("Тестовые данные успешно добавлены в базу данных")
    except Exception as e:
        logger.error(f"Ошибка при добавлении тестовых данных: {str(e)}")
    finally:
        # Закрываем соединение с базой данных
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main()) 