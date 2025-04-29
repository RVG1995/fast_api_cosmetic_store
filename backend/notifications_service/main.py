"""Модуль Notifications Service."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .settings_router import router as settings_router
from .cache import get_redis, close_redis

logger = logging.getLogger(__name__)

# Используем lifespan вместо on_event (FastAPI v2)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения: инициализация БД и Redis, и очистка ресурсов."""
    logging.basicConfig(level=logging.INFO)
    # Настройка логгера для модуля auth
    auth_logger = logging.getLogger("notifications_service.auth")
    auth_logger.setLevel(logging.INFO)
    
    # Инициализация БД и запуск консьюмера
    await init_db()
    # Инициализация Redis для кэша уведомлений
    await get_redis()
    yield
    # Закрытие соединения с Redis
    await close_redis()
    await engine.dispose()


# Создаем приложение с lifespan
app = FastAPI(title="Notifications Service", lifespan=lifespan)
# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(settings_router, prefix="/notifications", tags=["notifications"])

async def init_db():
    """Инициализировать базу данных (создать таблицы)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8005"))
    
    # Запуск с авто‑перезагрузкой только для этого сервиса
    service_dir = os.path.dirname(__file__)
    uvicorn.run(
        "notifications_service.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[service_dir]
    )
