import logging
from typing import Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from database import setup_database, get_session, engine
from cache import cache_service, close_redis_connection
from config import settings, get_cors_origins
from routers import (
    product_router,
    category_router,
    brand_router,
    country_router,
    subcategory_router,
    product_batch_router
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который должен выполниться при запуске приложения (startup)
    await setup_database()  # вызываем асинхронную функцию для создания таблиц или миграций
    logger.info("База данных сервиса продуктов инициализирована")
    
    # Инициализируем кэш
    await cache_service.initialize()
    
    yield  # здесь приложение будет работать
    # Код для завершения работы приложения (shutdown) можно добавить после yield, если нужно
    logger.info("Завершение работы сервиса продуктов")
    await close_redis_connection()
    await engine.dispose()  # корректное закрытие соединений с базой данных
    logger.info("Соединения с БД и Redis закрыты")

app = FastAPI(lifespan=lifespan)

# Создаем директорию для загрузки файлов
import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Настройка CORS
origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Разрешенные источники
    allow_credentials=True,
    allow_methods=["*"],        # Разрешенные методы (GET, POST и т.д.)
    allow_headers=["*"],        # Разрешенные заголовки
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Подключение всех роутеров
app.include_router(product_router)
app.include_router(category_router)
app.include_router(brand_router)
app.include_router(country_router)
app.include_router(subcategory_router)
app.include_router(product_batch_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8001, reload=True)
