from fastapi import FastAPI, Depends, HTTPException, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import logging
import os
from math import ceil
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
import sys

from database import get_session, setup_database, init_db
from models import OrderModel, OrderItemModel, OrderStatusModel, OrderStatusHistoryModel
from auth import User, get_current_user, check_admin_access, check_authenticated
from product_api import ProductAPI, get_product_api
from cart_api import CartAPI, get_cart_api
from email_service import EmailService
from database import engine
from routers.orders import router as order_router
from routers.orders import admin_router as admin_order_router
from routers.order_statuses import router as order_statuses_router
from cache import close_redis

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("order_service")

# Определяем функцию жизненного цикла
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Выполняется при запуске и остановке приложения.
    Инициализирует базу данных при запуске и закрывает соединения при остановке.
    """
    # Код, выполняемый при запуске приложения
    logger.info("Запуск сервиса заказов...")
    await setup_database()
    logger.info("Сервис заказов успешно запущен")
    
    yield  # здесь приложение будет работать
    
    # Код, выполняемый при остановке приложения
    logger.info("Завершение работы сервиса заказов...")
    
    # Закрытие соединений с Redis
    await close_redis()
    logger.info("Соединение с Redis закрыто")
    
    # Закрытие соединений с базой данных
    await engine.dispose()
    
    logger.info("Сервис заказов успешно остановлен")

# Создаем экземпляр FastAPI с использованием lifespan
app = FastAPI(
    title="Order Service API",
    description="API для управления заказами в интернет-магазине",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка путей к статическим файлам
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")

# Подключение роутеров
app.include_router(order_router)
app.include_router(admin_order_router)
app.include_router(order_statuses_router)

# Маршрут для проверки работоспособности сервиса
@app.get("/api/health", tags=["health"])
async def health_check():
    """
    Проверка работоспособности сервиса.
    Возвращает статус сервиса.
    """
    return {"status": "ok", "service": "order_service"}

# Запуск приложения
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8003"))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
    ) 