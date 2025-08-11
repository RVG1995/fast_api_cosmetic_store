"""Основной модуль сервиса аутентификации, содержащий конфигурацию FastAPI приложения и middleware."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import setup_database, engine, create_superadmin, create_default_user
from router import router as auth_router
from admin_router import router as admin_router
from app.services import (
    cache_service,
    bruteforce_protection
)
from config import settings, get_origins
from app.services.auth.keys_service import initialize_keys

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация Redis-клиентов при старте приложения"""
    logger.info("Инициализация RSA ключей для RS256/JWKS...")
    initialize_keys()
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

UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Получаем список разрешенных источников из конфигурации
origins = get_origins()

logger.info("Настройка CORS с разрешенными источниками: %s", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token", "Authorization", "Content-Type"],
    expose_headers=["*", "X-CSRF-Token"]  # Разрешаем доступ к заголовкам ответа
)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info("Получен запрос: %s %s", request.method, request.url)
    logger.info("Заголовки запроса: %s", request.headers)
    response = await call_next(request)
    logger.info("Ответ: %s", response.status_code)
    return response

app.include_router(auth_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000, reload=True)
