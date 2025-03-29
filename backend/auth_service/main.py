from fastapi import FastAPI
from database import setup_database, engine, create_superadmin, create_default_user
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from router import router as auth_router
from admin_router import router as admin_router
import logging
from app.services import (
    cache_service,
    bruteforce_protection
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация Redis-клиентов при старте приложения"""
    logger.info("Инициализация Redis-клиентов...")
    # Инициализируем кэш-сервис
    await cache_service.initialize() 
    # Инициализируем сервис защиты от брутфорса
    await bruteforce_protection.initialize()
    
    logger.info("Redis-клиенты успешно инициализированы")
    await setup_database()
    await create_superadmin()
    await create_default_user()
    yield 
    logger.info("Закрытие Redis-соединений...")
    
    # Закрываем соединение кэш-сервиса
    await cache_service.close()
    
    # Закрываем соединение сервиса защиты от брутфорса
    await bruteforce_protection.close()
    
    logger.info("Redis-соединения успешно закрыты")
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Расширяем список разрешенных источников
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1",
    # Добавляем и другие источники, которые могут быть использованы в разработке
]

logger.info(f"Настройка CORS с разрешенными источниками: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Разрешаем доступ к заголовкам ответа
)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Получен запрос: {request.method} {request.url}")
    logger.info(f"Заголовки запроса: {request.headers}")
    response = await call_next(request)
    logger.info(f"Ответ: {response.status_code}")
    return response

app.include_router(auth_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000, reload=True)
