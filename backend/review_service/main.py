from fastapi import FastAPI, Depends, Request, Response
from database import setup_database, engine
from cache import initialize_redis, close_redis_connection
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from routers.reviews import router as reviews_router
from routers.admin import router as admin_router
import logging
import os
from fastapi.staticfiles import StaticFiles

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Инициализация сервисов при запуске приложения и их корректное завершение
    """
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await setup_database()
    logger.info("База данных инициализирована")
    
    # Инициализация Redis
    logger.info("Инициализация Redis...")
    await initialize_redis()
    logger.info("Redis инициализирован")
    
    yield
    
    # Закрытие соединений при завершении работы
    logger.info("Закрытие соединений...")
    await close_redis_connection()
    await engine.dispose()
    logger.info("Соединения закрыты")

app = FastAPI(
    title="Review Service API",
    description="Сервис отзывов на товары и магазин",
    version="1.0.0",
    lifespan=lifespan
)

# Создание директории для статических файлов (если понадобится)
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Настройка CORS
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех запросов к API"""
    logger.info(f"Получен запрос: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Отправлен ответ: {response.status_code}")
    return response

# Добавление роутеров
app.include_router(reviews_router)
app.include_router(admin_router)

# Корневой эндпоинт с информацией о сервисе
@app.get("/", tags=["info"])
async def root():
    """Информация о сервисе отзывов"""
    return {
        "name": "Review Service API",
        "version": "1.0.0",
        "description": "Сервис отзывов на товары и магазин"
    }

# Проверка здоровья сервиса
@app.get("/health", tags=["info"])
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True) 