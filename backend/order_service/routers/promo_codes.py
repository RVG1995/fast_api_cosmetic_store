"""Модуль для управления промокодами через API.

Этот модуль предоставляет эндпоинты для создания, чтения, обновления и удаления промокодов,
а также для проверки их валидности.
"""

from typing import List
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import PromoCodeModel
from schemas import (
    PromoCodeCreate, PromoCodeUpdate, PromoCodeResponse,
    PromoCodeCheckRequest, PromoCodeCheckResponse
)
from services import check_promo_code
from dependencies import get_admin_user
from cache import invalidate_cache, CacheKeys

# Настройка логирования
logger = logging.getLogger("promo_code_router")

# Создание роутера для промокодов
router = APIRouter(
    prefix="/promo-codes",
    tags=["promo_codes"],
    responses={404: {"description": "Not found"}}
)

# Создание роутера для админ-панели
admin_router = APIRouter(
    prefix="/admin/promo-codes",
    tags=["admin_promo_codes"],
    responses={404: {"description": "Not found"}}
)

# Публичные эндпоинты


@router.post("/check", response_model=PromoCodeCheckResponse)
async def check_promo_code_endpoint(
    request: PromoCodeCheckRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Проверка валидности промокода

    - **code**: Код промокода
    - **email**: Email пользователя для проверки использования
    - **phone**: Телефон пользователя для проверки использования
    """
    try:
        is_valid, message, promo_code = await check_promo_code(
            session=session,
            code=request.code,
            email=request.email,
            phone=request.phone
        )

        response = PromoCodeCheckResponse(
            is_valid=is_valid,
            message=message,
            promo_code=PromoCodeResponse.model_validate(promo_code) if promo_code else None
        )

        if is_valid and promo_code:
            if promo_code.discount_percent is not None:
                response.discount_percent = promo_code.discount_percent
            if promo_code.discount_amount is not None:
                response.discount_amount = promo_code.discount_amount

        return response
    except Exception as e:
        logger.error("Ошибка при проверке промокода: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при проверке промокода"
        ) from e

# Административные эндпоинты


@admin_router.get("", response_model=List[PromoCodeResponse])
async def get_all_promo_codes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Получение списка всех промокодов (только для администраторов)

    - **skip**: Количество пропускаемых записей
    - **limit**: Максимальное количество возвращаемых записей
    """
    if not current_user or not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )

    promo_codes = await PromoCodeModel.get_all(session, skip, limit)
    return [PromoCodeResponse.model_validate(code) for code in promo_codes]


@admin_router.get("/active", response_model=List[PromoCodeResponse])
async def get_active_promo_codes(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Получение списка активных промокодов (только для администраторов)
    """
    if not current_user or not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    promo_codes = await PromoCodeModel.get_active(session)
    return [PromoCodeResponse.model_validate(code) for code in promo_codes]


@admin_router.get("/{promo_code_id}", response_model=PromoCodeResponse)
async def get_promo_code(
    promo_code_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Получение информации о промокоде по ID (только для администраторов)

    - **promo_code_id**: ID промокода
    """
    if not current_user or not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    promo_code = await session.get(PromoCodeModel, promo_code_id)
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Промокод с ID {promo_code_id} не найден"
        )
    return PromoCodeResponse.model_validate(promo_code)


@admin_router.post("", response_model=PromoCodeResponse,
                   status_code=status.HTTP_201_CREATED)
async def create_promo_code(
    promo_code_data: PromoCodeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Создание нового промокода (только для администраторов)

    - **promo_code_data**: Данные для создания промокода
    """
    try:
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Проверяем, что код промокода уникален
        existing_code = await PromoCodeModel.get_by_code(session, promo_code_data.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Промокод с кодом '{promo_code_data.code}' уже существует")

        # Создаем новый промокод
        promo_code = PromoCodeModel(
            code=promo_code_data.code,
            discount_percent=promo_code_data.discount_percent,
            discount_amount=promo_code_data.discount_amount,
            valid_until=promo_code_data.valid_until,
            is_active=promo_code_data.is_active
        )
        session.add(promo_code)
        await session.commit()
        await session.refresh(promo_code)

        # Инвалидируем кэш
        await invalidate_cache(CacheKeys.PROMO_CODES)

        return PromoCodeResponse.model_validate(promo_code)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при создании промокода: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании промокода"
        ) from e


@admin_router.put("/{promo_code_id}", response_model=PromoCodeResponse)
async def update_promo_code(
    promo_code_id: int = Path(..., ge=1),
    promo_code_data: PromoCodeUpdate = Body(...),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Обновление промокода (только для администраторов)

    - **promo_code_id**: ID промокода
    - **promo_code_data**: Данные для обновления промокода
    """
    try:
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Получаем промокод из БД
        promo_code = await session.get(PromoCodeModel, promo_code_id)
        if not promo_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Промокод с ID {promo_code_id} не найден"
            )

        # Проверяем, что код промокода уникален, если он изменяется
        if promo_code_data.code is not None and promo_code_data.code != promo_code.code:
            existing_code = await PromoCodeModel.get_by_code(session, promo_code_data.code)
            if existing_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Промокод с кодом '{promo_code_data.code}' уже существует")
            promo_code.code = promo_code_data.code

        # Обновляем остальные поля, если они указаны
        if promo_code_data.discount_percent is not None:
            promo_code.discount_percent = promo_code_data.discount_percent
            promo_code.discount_amount = None  # Сбрасываем фиксированную скидку

        if promo_code_data.discount_amount is not None:
            promo_code.discount_amount = promo_code_data.discount_amount
            promo_code.discount_percent = None  # Сбрасываем процентную скидку

        if promo_code_data.valid_until is not None:
            promo_code.valid_until = promo_code_data.valid_until

        if promo_code_data.is_active is not None:
            promo_code.is_active = promo_code_data.is_active

        # Обновляем время последнего обновления
        promo_code.updated_at = datetime.now()

        # Сохраняем изменения в БД
        await session.commit()
        await session.refresh(promo_code)

        # Инвалидируем кэш
        await invalidate_cache(CacheKeys.PROMO_CODES)

        return PromoCodeResponse.model_validate(promo_code)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при обновлении промокода: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении промокода"
        ) from e


@admin_router.delete("/{promo_code_id}",
                     status_code=status.HTTP_204_NO_CONTENT)
async def delete_promo_code(
    promo_code_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user)
):
    """
    Удаление промокода (только для администраторов)

    - **promo_code_id**: ID промокода
    """
    try:
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Получаем промокод из БД
        promo_code = await session.get(PromoCodeModel, promo_code_id)
        if not promo_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Промокод с ID {promo_code_id} не найден"
            )

        # Удаляем промокод
        await session.delete(promo_code)
        await session.commit()

        # Инвалидируем кэш
        await invalidate_cache(CacheKeys.PROMO_CODES)

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при удалении промокода: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении промокода"
        ) from e
