from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Annotated

from models import BrandModel
from schema import BrandSchema, BrandAddSchema, BrandUpdateSchema
from database import get_session
from auth import require_admin, get_current_user
from cache import cache_get, cache_set, cache_delete_pattern, CACHE_KEYS, DEFAULT_CACHE_TTL, invalidate_cache

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
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['brands']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные брендов получены из кэша: {cache_key}")
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

@router.post('', response_model=BrandSchema)
async def add_brand(
    brand_data: BrandAddSchema,
    session: SessionDep,
    admin = Depends(require_admin)
):
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
        logger.error(f"Ошибка при добавлении бренда: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бренд с таким названием уже существует"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Неизвестная ошибка при добавлении бренда: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при добавлении бренда"
        )

@router.put("/{brand_id}", response_model=BrandSchema)
async def update_brand(
    brand_id: int, 
    brand_data: BrandUpdateSchema,
    session: SessionDep,
    admin = Depends(require_admin)
):
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
        logger.error(f"Ошибка при обновлении бренда: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бренд с таким названием уже существует"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Неизвестная ошибка при обновлении бренда: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении бренда"
        )

@router.get('/{brand_id}', response_model=BrandSchema)
async def get_brand_by_id(brand_id: int, session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['brands']}{brand_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные бренда получены из кэша: {cache_key}")
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

@router.delete("/{brand_id}", status_code=204)
async def delete_brand(
    brand_id: int,
    session: SessionDep,
    admin = Depends(require_admin)
):
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
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно удалить бренд, т.к. существуют связанные записи"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Неизвестная ошибка при удалении бренда: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении бренда"
        )
