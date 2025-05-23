from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.favorites import router as favorites_router
from config import get_cors_origins
from database import setup_database,engine
from cache import cache_service
import logging
from contextlib import asynccontextmanager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_database()
    await cache_service.initialize()
    yield 
    logger.info("Закрытие Redis-соединений...")

    # Закрываем соединение кэш-сервиса
    await cache_service.close()
    
    logger.info("Redis-соединения успешно закрыты")
    await engine.dispose()

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(favorites_router) 




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8007, reload=True)