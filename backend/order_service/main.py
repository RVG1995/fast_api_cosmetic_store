"""
Сервис управления заказами на FastAPI.
Обрабатывает заказы, отслеживает их статусы и связанные операции.
"""

import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import setup_database
from database import engine
from routers.orders import router as orders_router, admin_router as orders_admin_router
from routers.order_statuses import router as order_statuses_router
from routers.promo_codes import router as promo_codes_router, admin_router as promo_codes_admin_router
from routers.dadata import router as dadata_router
from cache import close_redis, cache_service
from init_data import init_order_statuses
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
    await init_order_statuses()
    
    # Инициализируем кэш
    await cache_service.initialize()
    logger.info("Кэш инициализирован")
    
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
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
    "http://localhost:8003",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
    "http://127.0.0.1:8002",
    "http://127.0.0.1:8003",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Credentials"],
)

# Настройка путей к статическим файлам
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")

# Подключение роутеров
app.include_router(orders_router)
app.include_router(orders_admin_router)
app.include_router(order_statuses_router)
app.include_router(promo_codes_router)
app.include_router(promo_codes_admin_router)
app.include_router(dadata_router)

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
