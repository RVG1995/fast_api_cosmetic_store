"""Маршруты для работы со странами (CRUD + кэширование)."""

import logging
from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import CountryModel
from schema import CountrySchema, CountryAddSchema, CountryUpdateSchema
from database import get_session
from auth import require_admin
from cache import cache_get, cache_set, CACHE_KEYS, DEFAULT_CACHE_TTL, invalidate_cache

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("countries_router")

# Создание роутера
router = APIRouter(
    prefix="/countries",
    tags=["countries"],
    responses={404: {"description": "Not found"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.get('', response_model=List[CountrySchema])
async def get_countries(session: SessionDep):
    """Получить список всех стран."""
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['countries']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Данные стран получены из кэша: %s", cache_key)
        return cached_data
    
    # Если данных в кэше нет, делаем запрос к БД
    query = select(CountryModel).order_by(CountryModel.name)
    result = await session.execute(query)
    countries = result.scalars().all()
    
    # Преобразуем для кэширования и сохраняем
    countries_list = [country.__dict__ for country in countries]
    for country in countries_list:
        if '_sa_instance_state' in country:
            del country['_sa_instance_state']
    
    # Сохраняем в кэш
    await cache_set(cache_key, countries_list, DEFAULT_CACHE_TTL)
    
    return countries

@router.post('', response_model=CountrySchema,dependencies=[Depends(require_admin)])
async def add_country(
    country_data: CountryAddSchema,
    session: SessionDep,
):
    # Создаем новую страну
    new_country = CountryModel(**country_data.model_dump())
    
    # Добавляем в БД
    session.add(new_country)
    
    try:
        await session.commit()
        await session.refresh(new_country)
        
        # Инвалидируем кэш стран
        await invalidate_cache(f"{CACHE_KEYS['countries']}*")
        
        return new_country
    except IntegrityError as e:
        await session.rollback()
        logger.error("Ошибка при добавлении страны: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Страна с таким названием уже существует"
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Неизвестная ошибка при добавлении страны: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при добавлении страны"
        ) from e

@router.put("/{country_id}", response_model=CountrySchema,dependencies=[Depends(require_admin)])
async def update_country(
    country_id: int,
    country_data: CountryUpdateSchema,
    session: SessionDep,
):
    """Обновить существующую страну по ID."""
    # Находим страну по ID
    query = select(CountryModel).where(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страна не найдена"
        )
    
    # Обновляем поля страны
    for field, value in country_data.model_dump(exclude_unset=True).items():
        setattr(country, field, value)
    
    try:
        await session.commit()
        await session.refresh(country)
        
        # Инвалидируем кэш стран и связанных продуктов
        await invalidate_cache(f"{CACHE_KEYS['countries']}*")
        await invalidate_cache(f"{CACHE_KEYS['products']}*")
        
        return country
    except IntegrityError as e:
        await session.rollback()
        logger.error("Ошибка при обновлении страны: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Страна с таким названием уже существует"
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Неизвестная ошибка при обновлении страны: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении страны"
        ) from e

@router.get('/{country_id}', response_model=CountrySchema)
async def get_country_by_id(country_id: int, session: SessionDep):
    """Получить страну по ID."""
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['countries']}{country_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info("Данные страны получены из кэша: %s", cache_key)
        return cached_data
    
    # Если данных в кэше нет, делаем запрос к БД
    query = select(CountryModel).where(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страна не найдена"
        )
    
    # Преобразуем для кэширования
    country_dict = country.__dict__.copy()
    if '_sa_instance_state' in country_dict:
        del country_dict['_sa_instance_state']
    
    # Сохраняем в кэш
    await cache_set(cache_key, country_dict, DEFAULT_CACHE_TTL)
    
    return country

@router.delete("/{country_id}", status_code=204,dependencies=[Depends(require_admin)])
async def delete_country(
    country_id: int,
    session: SessionDep,
):
    """Удалить страну по ID."""
    # Находим страну по ID
    query = select(CountryModel).where(CountryModel.id == country_id)
    result = await session.execute(query)
    country = result.scalars().first()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страна не найдена"
        )
    
    # Удаляем страну
    try:
        await session.delete(country)
        await session.commit()
        
        # Инвалидируем кэш стран и связанных продуктов
        await invalidate_cache(f"{CACHE_KEYS['countries']}*")
        await invalidate_cache(f"{CACHE_KEYS['products']}*")
        
        return None
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно удалить страну, т.к. существуют связанные записи"
        ) from e
    except Exception as e:
        await session.rollback()
        logger.error("Неизвестная ошибка при удалении страны: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении страны"
        ) from e
