"""
Сервис управления заказами на FastAPI.
Обрабатывает заказы, отслеживает их статусы и связанные операции.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.dadata import router as dadata_router
from routers.boxberry import router as boxberry_router
from cache import close_redis, cache_service
from config import settings, get_cors_origins

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("delivery_service")

# Определяем функцию жизненного цикла
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Выполняется при запуске и остановке приложения.
    Инициализирует базу данных при запуске и закрывает соединения при остановке.
    """
    # Код, выполняемый при запуске приложения
    logger.info("Запуск сервиса доставки...")
    
    # Инициализируем кэш
    await cache_service.initialize()
    logger.info("Кэш инициализирован")
    
    logger.info("Сервис доставки успешно запущен")
    
    yield  # здесь приложение будет работать
    
    # Код, выполняемый при остановке приложения
    logger.info("Завершение работы сервиса доставки...")
    
    # Закрытие соединений с Redis
    await close_redis()
    logger.info("Соединение с Redis закрыто")    
    logger.info("Сервис доставки успешно остановлен")

# Создаем экземпляр FastAPI с использованием lifespan
app = FastAPI(
    title="Delivery Service API",
    description="API для управления доставкой в интернет-магазине",
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

app.include_router(dadata_router, prefix="/delivery")
app.include_router(boxberry_router, prefix="/delivery")

# Маршрут для проверки работоспособности сервиса
@app.get("/api/health", tags=["health"])
async def health_check():
    """
    Проверка работоспособности сервиса.
    Возвращает статус сервиса.
    """
    return {"status": "ok", "service": "delivery_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8006, reload=True)
