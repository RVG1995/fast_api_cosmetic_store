"""
Сервис управления заказами на FastAPI.
Обрабатывает заказы, отслеживает их статусы и связанные операции.
"""

import logging
from contextlib import asynccontextmanager

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
from config import settings, get_cors_origins

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
origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Credentials"],
)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8003, reload=True)
