"""Модуль для управления статусами заказов через API.

Этот модуль предоставляет эндпоинты для создания, чтения, обновления и удаления статусов заказов.
"""

from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import OrderStatusModel
from schemas import OrderStatusCreate, OrderStatusUpdate, OrderStatusResponse
from dependencies import get_admin_user
from cache import (
    get_cached_order_statuses, cache_order_statuses,
    invalidate_order_statuses_cache
)

# Настройка логирования
logger = logging.getLogger("order_status_router")

# Создание роутера
router = APIRouter(
    prefix="/order-statuses",
    tags=["order_statuses"],
    responses={404: {"description": "Not found"}},
)

@router.get("", response_model=List[OrderStatusResponse])
async def list_order_statuses(
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка всех статусов заказов.
    """
    try:
        # Пытаемся получить данные из кэша
        cached_statuses = await get_cached_order_statuses()
        if cached_statuses:
            logger.info("Данные о статусах заказов получены из кэша")
            return cached_statuses

        # Если данных нет в кэше, получаем из БД
        statuses = await OrderStatusModel.get_all(session)

        # Преобразуем модели в схемы
        status_responses = [OrderStatusResponse.model_validate(status) for status in statuses]

        # Кэшируем результат
        await cache_order_statuses(status_responses)
        logger.info("Данные о статусах заказов добавлены в кэш")

        return status_responses
    except Exception as e:
        logger.error("Ошибка при получении списка статусов заказов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка статусов заказов",
        ) from e

@router.get("/{status_id}", response_model=OrderStatusResponse)
async def get_order_status(
    status_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации о статусе заказа по ID.

    - **status_id**: ID статуса заказа
    """
    try:
        # Получаем статус заказа
        order_status = await OrderStatusModel.get_by_id(session, status_id)

        if not order_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус заказа с ID {status_id} не найден",
            )

        return OrderStatusResponse.model_validate(order_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при получении информации о статусе заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о статусе заказа",
        ) from e

@router.post("", response_model=OrderStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_order_status(
    status_data: OrderStatusCreate,
    current_user = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание нового статуса заказа (только для администраторов).

    - **status_data**: Данные для создания статуса заказа
    """
    try:
        # Проверяем права доступа
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Проверяем, существует ли статус с таким именем
        query = select(OrderStatusModel).filter(OrderStatusModel.name == status_data.name)
        result = await session.execute(query)
        existing_status = result.scalars().first()

        if existing_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Статус заказа с именем '{status_data.name}' уже существует",
            )

        # Создаем новый статус заказа
        order_status = OrderStatusModel(
            name=status_data.name,
            description=status_data.description,
            color=status_data.color,
            allow_cancel=status_data.allow_cancel,
            is_final=status_data.is_final,
            sort_order=status_data.sort_order
        )
        session.add(order_status)
        await session.commit()
        await session.refresh(order_status)

        # Инвалидируем кэш статусов заказов
        await invalidate_order_statuses_cache()
        logger.info(
            "Кэш статусов заказов инвалидирован после создания нового статуса: %s",
            status_data.name
        )
        logger.info(
            "Пользователь %s создал новый статус заказа: %s",
            current_user.username,
            status_data.name
        )

        return OrderStatusResponse.model_validate(order_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при создании статуса заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании статуса заказа",
        ) from e

@router.put("/{status_id}", response_model=OrderStatusResponse)
async def update_order_status(
    status_id: int = Path(..., ge=1),
    status_data: OrderStatusUpdate = None,
    current_user = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление информации о статусе заказа (только для администраторов).

    - **status_id**: ID статуса заказа
    - **status_data**: Данные для обновления
    """
    try:
        # Проверяем права доступа
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Получаем статус заказа
        order_status = await OrderStatusModel.get_by_id(session, status_id)

        if not order_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус заказа с ID {status_id} не найден",
            )

        # Проверяем, существует ли статус с таким именем (если имя изменяется)
        if status_data.name is not None and status_data.name != order_status.name:
            query = select(OrderStatusModel).filter(OrderStatusModel.name == status_data.name)
            result = await session.execute(query)
            existing_status = result.scalars().first()

            if existing_status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Статус заказа с именем '{status_data.name}' уже существует",
                )

        # Обновляем данные статуса заказа
        if status_data.name is not None:
            order_status.name = status_data.name

        if status_data.description is not None:
            order_status.description = status_data.description

        if status_data.color is not None:
            order_status.color = status_data.color

        if status_data.allow_cancel is not None:
            order_status.allow_cancel = status_data.allow_cancel

        if status_data.is_final is not None:
            order_status.is_final = status_data.is_final

        if status_data.sort_order is not None:
            order_status.sort_order = status_data.sort_order

        await session.commit()
        await session.refresh(order_status)

        # Инвалидируем кэш статусов заказов
        await invalidate_order_statuses_cache()
        logger.info(
            "Кэш статусов заказов инвалидирован после обновления статуса с ID: %s",
            status_id
        )
        logger.info(
            "Пользователь %s обновил статус заказа с ID: %s",
            current_user.username,
            status_id
        )

        return OrderStatusResponse.model_validate(order_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при обновлении статуса заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении статуса заказа",
        ) from e

@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_status(
    status_id: int = Path(..., ge=1),
    current_user = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Удаление статуса заказа (только для администраторов).

    - **status_id**: ID статуса заказа
    """
    try:
        # Проверяем права доступа
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )

        # Получаем статус заказа
        order_status = await OrderStatusModel.get_by_id(session, status_id)

        if not order_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус заказа с ID {status_id} не найден",
            )

        # Проверяем, используется ли статус в заказах
        query = (
            select(OrderStatusModel)
            .join(OrderStatusModel.orders)
            .filter(OrderStatusModel.id == status_id)
        )
        result = await session.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Невозможно удалить статус заказа с ID {status_id}, "
                    f"так как он используется в заказах"
                ),
            )

        # Удаляем статус заказа
        await session.delete(order_status)
        await session.commit()

        # Инвалидируем кэш статусов заказов
        await invalidate_order_statuses_cache()
        logger.info(
            "Кэш статусов заказов инвалидирован после удаления статуса с ID: %s",
            status_id
        )
        logger.info(
            "Пользователь %s удалил статус заказа с ID: %s",
            current_user.username,
            status_id
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при удалении статуса заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении статуса заказа",
        ) from e
