from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Annotated

from models import SubCategoryModel, CategoryModel
from schema import SubCategorySchema, SubCategoryAddSchema, SubCategoryUpdateSchema
from database import get_session
from auth import require_admin, get_current_user
from cache import cache_get, cache_set, cache_delete_pattern, CACHE_KEYS, DEFAULT_CACHE_TTL, invalidate_cache

import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subcategories_router")

# Создание роутера
router = APIRouter(
    prefix="/subcategories",
    tags=["subcategories"],
    responses={404: {"description": "Not found"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.get('', response_model=List[SubCategorySchema])
async def get_subcategories(session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['subcategories']}all"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные подкатегорий получены из кэша: {cache_key}")
        return cached_data
    
    # Если данных в кэше нет, делаем запрос к БД
    query = select(SubCategoryModel).order_by(SubCategoryModel.name)
    result = await session.execute(query)
    subcategories = result.scalars().all()
    
    # Преобразуем для кэширования и сохраняем
    subcategories_list = [subcat.__dict__ for subcat in subcategories]
    for subcat in subcategories_list:
        if '_sa_instance_state' in subcat:
            del subcat['_sa_instance_state']
    
    # Сохраняем в кэш
    await cache_set(cache_key, subcategories_list, DEFAULT_CACHE_TTL)
    
    return subcategories

@router.post('', response_model=SubCategorySchema)
async def add_subcategory(
    subcategory_data: SubCategoryAddSchema,
    session: SessionDep,
    admin = Depends(require_admin)
):
    # Проверка наличия родительской категории
    category_query = select(CategoryModel).where(CategoryModel.id == subcategory_data.category_id)
    category_result = await session.execute(category_query)
    category = category_result.scalars().first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Указанная родительская категория не найдена"
        )
    
    # Создаем новую подкатегорию
    new_subcategory = SubCategoryModel(**subcategory_data.model_dump())
    
    # Добавляем в БД
    session.add(new_subcategory)
    
    try:
        await session.commit()
        await session.refresh(new_subcategory)
        
        # Инвалидируем кэш подкатегорий и категорий
        await invalidate_cache(f"{CACHE_KEYS['subcategories']}*")
        await invalidate_cache(f"{CACHE_KEYS['categories']}*")
        
        return new_subcategory
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Ошибка при добавлении подкатегории: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Подкатегория с таким названием уже существует"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Неизвестная ошибка при добавлении подкатегории: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при добавлении подкатегории"
        )

@router.put("/{subcategory_id}", response_model=SubCategorySchema)
async def update_subcategory(
    subcategory_id: int, 
    subcategory_data: SubCategoryUpdateSchema,
    session: SessionDep,
    admin = Depends(require_admin)
):
    # Находим подкатегорию по ID
    query = select(SubCategoryModel).where(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подкатегория не найдена"
        )
    
    # Проверка наличия родительской категории, если она обновляется
    if subcategory_data.category_id is not None:
        category_query = select(CategoryModel).where(CategoryModel.id == subcategory_data.category_id)
        category_result = await session.execute(category_query)
        category = category_result.scalars().first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Указанная родительская категория не найдена"
            )
    
    # Обновляем поля подкатегории
    for field, value in subcategory_data.model_dump(exclude_unset=True).items():
        setattr(subcategory, field, value)
    
    try:
        await session.commit()
        await session.refresh(subcategory)
        
        # Инвалидируем кэш подкатегорий, категорий и связанных продуктов
        await invalidate_cache(f"{CACHE_KEYS['subcategories']}*")
        await invalidate_cache(f"{CACHE_KEYS['categories']}*")
        await invalidate_cache(f"{CACHE_KEYS['products']}*")
        
        return subcategory
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Ошибка при обновлении подкатегории: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Подкатегория с таким названием уже существует"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Неизвестная ошибка при обновлении подкатегории: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении подкатегории"
        )

@router.get('/{subcategory_id}', response_model=SubCategorySchema)
async def get_subcategory_by_id(subcategory_id: int, session: SessionDep):
    # Формируем ключ кэша
    cache_key = f"{CACHE_KEYS['subcategories']}{subcategory_id}"
    
    # Пробуем получить данные из кэша
    cached_data = await cache_get(cache_key)
    if cached_data:
        logger.info(f"Данные подкатегории получены из кэша: {cache_key}")
        return cached_data
    
    # Если данных в кэше нет, делаем запрос к БД
    query = select(SubCategoryModel).where(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подкатегория не найдена"
        )
    
    # Преобразуем для кэширования
    subcategory_dict = subcategory.__dict__.copy()
    if '_sa_instance_state' in subcategory_dict:
        del subcategory_dict['_sa_instance_state']
    
    # Сохраняем в кэш
    await cache_set(cache_key, subcategory_dict, DEFAULT_CACHE_TTL)
    
    return subcategory

@router.delete("/{subcategory_id}", status_code=204)
async def delete_subcategory(
    subcategory_id: int,
    session: SessionDep,
    admin = Depends(require_admin)
):
    # Находим подкатегорию по ID
    query = select(SubCategoryModel).where(SubCategoryModel.id == subcategory_id)
    result = await session.execute(query)
    subcategory = result.scalars().first()
    
    if not subcategory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подкатегория не найдена"
        )
    
    # Удаляем подкатегорию
    try:
        await session.delete(subcategory)
        await session.commit()
        
        # Инвалидируем кэш подкатегорий, категорий и связанных продуктов
        await invalidate_cache(f"{CACHE_KEYS['subcategories']}*")
        await invalidate_cache(f"{CACHE_KEYS['categories']}*")
        await invalidate_cache(f"{CACHE_KEYS['products']}*")
        
        return None
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно удалить подкатегорию, т.к. существуют связанные записи"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Неизвестная ошибка при удалении подкатегории: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении подкатегории"
        )
