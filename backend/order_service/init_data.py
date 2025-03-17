import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import os
from dotenv import load_dotenv

from models import OrderStatusModel, Base
from database import DATABASE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_data")

# Загрузка переменных окружения
load_dotenv()

# Создание подключения к базе данных
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Список базовых статусов заказа
DEFAULT_ORDER_STATUSES = [
    {
        "name": "Новый",
        "description": "Заказ только что создан",
        "color": "#3498db",  # Синий
        "allow_cancel": True,
        "is_final": False,
        "sort_order": 1
    },
    {
        "name": "В обработке",
        "description": "Заказ обрабатывается менеджером",
        "color": "#f1c40f",  # Желтый
        "allow_cancel": True,
        "is_final": False,
        "sort_order": 2
    },
    {
        "name": "Оплачен",
        "description": "Заказ оплачен",
        "color": "#2ecc71",  # Зеленый
        "allow_cancel": True,
        "is_final": False,
        "sort_order": 3
    },
    {
        "name": "Отправлен",
        "description": "Заказ отправлен",
        "color": "#9b59b6",  # Фиолетовый
        "allow_cancel": False,
        "is_final": False,
        "sort_order": 4
    },
    {
        "name": "Доставлен",
        "description": "Заказ доставлен",
        "color": "#27ae60",  # Темно-зеленый
        "allow_cancel": False,
        "is_final": True,
        "sort_order": 5
    },
    {
        "name": "Отменен",
        "description": "Заказ отменен",
        "color": "#e74c3c",  # Красный
        "allow_cancel": False,
        "is_final": True,
        "sort_order": 6
    }
]

async def init_order_statuses():
    """
    Инициализация статусов заказа в базе данных.
    Добавляет только отсутствующие статусы, не затрагивая существующие.
    """
    async with async_session() as session:
        # Проверяем существующие статусы
        query = select(OrderStatusModel)
        result = await session.execute(query)
        existing_statuses = result.scalars().all()
        
        # Создаем словарь существующих статусов по имени
        existing_status_names = {status.name for status in existing_statuses}
        
        # Добавляем только отсутствующие статусы
        statuses_to_add = []
        for status_data in DEFAULT_ORDER_STATUSES:
            if status_data["name"] not in existing_status_names:
                status = OrderStatusModel(**status_data)
                statuses_to_add.append(status)
        
        if statuses_to_add:
            session.add_all(statuses_to_add)
            await session.commit()
            logger.info(f"Добавлено {len(statuses_to_add)} новых статусов заказа")
        else:
            logger.info("Все статусы заказа уже существуют в базе данных")
