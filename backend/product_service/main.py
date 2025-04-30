import os
import logging
from typing import Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from database import setup_database, get_session, engine
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# Импортируем функции для работы с кэшем
from cache import cache_service,close_redis_connection
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

UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
# Настройка CORS
origins = [
    "http://localhost:3000",  # адрес вашего фронтенда
    "http://127.0.0.1:3000",  # дополнительный адрес для тестирования
    # можно добавить другие источники, если нужно
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Разрешенные источники
    allow_credentials=True,
    allow_methods=["*"],        # Разрешенные методы (GET, POST и т.д.)
    allow_headers=["*"],        # Разрешенные заголовки
)

SessionDep = Annotated[AsyncSession,Depends(get_session)]

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
