"""Роуты для работы с брендами (brands) в сервисе продуктов."""

from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import BrandModel
from schema import BrandSchema, BrandAddSchema, BrandUpdateSchema
from database import get_session
from auth import require_admin
from cache import cache_get, cache_set, CACHE_KEYS, DEFAULT_CACHE_TTL, invalidate_cache

import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brands_router")

# Создание роутера
router = APIRouter(
    prefix="/brands",
    tags=["brands"],
    responses={404: {"description": "Not found"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.get('', response_model=List[BrandSchema])
async def get_brands(session: SessionDep):
    """Получить список всех брендов."""
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['brands']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Данные брендов получены из кэша: %s", cache_key)
        return cached_data
    
    # Если данных в кэше нет, делаем запрос к БД
    query = select(BrandModel).order_by(BrandModel.name)
    result = await session.execute(query)
    brands = result.scalars().all()
    
    # Преобразуем для кэширования и сохраняем
    brands_list = [brand.__dict__ for brand in brands]
    for brand in brands_list:
        if '_sa_instance_state' in brand:
            del brand['_sa_instance_state']
    
    # Сохраняем в кэш
    await cache_set(cache_key, brands_list, DEFAULT_CACHE_TTL)
    
    return brands

@router.post('', response_model=BrandSchema,dependencies=[Depends(require_admin)])
async def add_brand(
    brand_data: BrandAddSchema,
    session: SessionDep,
):
    """Добавить новый бренд."""
    # Создаем новый бренд
    new_brand = BrandModel(**brand_data.model_dump())
    
    # Добавляем в БД
    session.add(new_brand)
    
    try:
        await session.commit()
        await session.refresh(new_brand)
        
        # Инвалидируем кэш брендов
        await invalidate_cache(f"{CACHE_KEYS['brands']}*")
        
        return new_brand
    except IntegrityError as e:
        await session.rollback()
        logger.error("Ошибка при добавлении бренда: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бренд с таким названием уже существует"
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Неизвестная ошибка при добавлении бренда: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при добавлении бренда"
        ) from e

@router.put("/{brand_id}", response_model=BrandSchema,dependencies=[Depends(require_admin)])
async def update_brand(
    brand_id: int, 
    brand_data: BrandUpdateSchema,
    session: SessionDep,
):
    """Обновить бренд по ID."""
    # Находим бренд по ID
    query = select(BrandModel).where(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бренд не найден"
        )
    
    # Обновляем поля бренда
    for field, value in brand_data.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    
    try:
        await session.commit()
        await session.refresh(brand)
        
        # Инвалидируем кэш брендов и связанных продуктов
        await invalidate_cache(f"{CACHE_KEYS['brands']}*")
        await invalidate_cache(f"{CACHE_KEYS['products']}*")
        
        return brand
    except IntegrityError as e:
        await session.rollback()
        logger.error("Ошибка при обновлении бренда: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бренд с таким названием уже существует"
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Неизвестная ошибка при обновлении бренда: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении бренда"
        ) from e

@router.get('/{brand_id}', response_model=BrandSchema)
async def get_brand_by_id(brand_id: int, session: SessionDep):
    """Получить бренд по ID."""
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['brands']}{brand_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Данные бренда получены из кэша: %s", cache_key)
        return cached_data
    
    # Если данных в кэше нет, делаем запрос к БД
    query = select(BrandModel).where(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бренд не найден"
        )
    
    # Преобразуем для кэширования
    brand_dict = brand.__dict__.copy()
    if '_sa_instance_state' in brand_dict:
        del brand_dict['_sa_instance_state']
    
    # Сохраняем в кэш
    await cache_set(cache_key, brand_dict, DEFAULT_CACHE_TTL)
    
    return brand

@router.delete("/{brand_id}", status_code=204,dependencies=[Depends(require_admin)])
async def delete_brand(
    brand_id: int,
    session: SessionDep,
):
    """Удалить бренд по ID."""
    # Находим бренд по ID
    query = select(BrandModel).where(BrandModel.id == brand_id)
    result = await session.execute(query)
    brand = result.scalars().first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бренд не найден"
        )
    
    # Удаляем бренд
    try:
        await session.delete(brand)
        await session.commit()
        
        # Инвалидируем кэш брендов и связанных продуктов
        await invalidate_cache(f"{CACHE_KEYS['brands']}*")
        await invalidate_cache(f"{CACHE_KEYS['products']}*")
        
        return None
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно удалить бренд, т.к. существуют связанные записи"
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Неизвестная ошибка при удалении бренда: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении бренда"
        ) from e
