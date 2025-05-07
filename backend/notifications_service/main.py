"""FastAPI приложение для обработки уведомлений."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from settings_router import router as settings_router
from cache import get_redis, close_redis

logger = logging.getLogger(__name__)

# Используем lifespan вместо on_event (FastAPI v2)
@asynccontextmanager
async def lifespan(app: FastAPI):
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
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True) 