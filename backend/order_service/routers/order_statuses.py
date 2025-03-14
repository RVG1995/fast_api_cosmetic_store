from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import logging

from database import get_db
from models import OrderStatusModel
from schemas import OrderStatusCreate, OrderStatusUpdate, OrderStatusResponse
from dependencies import get_admin_user, get_current_user

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
        # Получаем все статусы заказов
        statuses = await OrderStatusModel.get_all(session)
        
        return [OrderStatusResponse.from_orm(status) for status in statuses]
    except Exception as e:
        logger.error(f"Ошибка при получении списка статусов заказов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка статусов заказов",
        )

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
        
        return OrderStatusResponse.from_orm(order_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о статусе заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о статусе заказа",
        )

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
        
        return OrderStatusResponse.from_orm(order_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании статуса заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании статуса заказа",
        )

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
        
        return OrderStatusResponse.from_orm(order_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении статуса заказа",
        )

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
        # Получаем статус заказа
        order_status = await OrderStatusModel.get_by_id(session, status_id)
        
        if not order_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус заказа с ID {status_id} не найден",
            )
        
        # Проверяем, используется ли статус в заказах
        query = select(OrderStatusModel).join(OrderStatusModel.orders).filter(OrderStatusModel.id == status_id)
        result = await session.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно удалить статус заказа с ID {status_id}, так как он используется в заказах",
            )
        
        # Удаляем статус заказа
        await session.delete(order_status)
        await session.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении статуса заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении статуса заказа",
        ) 