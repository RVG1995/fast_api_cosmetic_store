from typing import List, Optional, Union, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging

from schemas import (
    PaymentStatusCreate,
    PaymentStatusUpdate,
    PaymentStatusResponse
)
from models import PaymentStatusModel
from dependencies import get_db, get_current_user, get_admin_user

# Настройка логирования
logger = logging.getLogger("payment_statuses")

router = APIRouter(
    prefix="/payment-statuses",
    tags=["payment-statuses"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=List[PaymentStatusResponse])
async def list_payment_statuses(
    session: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Получить список всех статусов оплаты.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
        
    logger.info(f"User ID {current_user.get('user_id')} requested payment statuses list")
    payment_statuses = await PaymentStatusModel.get_all(session, skip=skip, limit=limit)
    return payment_statuses


@router.get("/{payment_status_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_status_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Получить статус оплаты по ID.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
        
    logger.info(f"User ID {current_user.get('user_id')} requested payment status with ID {payment_status_id}")
    payment_status = await PaymentStatusModel.get_by_id(session, payment_status_id)
    if not payment_status:
        logger.warning(f"Payment status with ID {payment_status_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment status not found"
        )
    return payment_status


@router.post("", response_model=PaymentStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_status(
    payment_status: PaymentStatusCreate,
    session: AsyncSession = Depends(get_db),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Создать новый статус оплаты.
    """
    logger.info(f"Admin (user ID {admin_user.get('user_id')}) creating new payment status: {payment_status}")
    
    try:
        new_payment_status = await PaymentStatusModel.create(session, payment_status)
        logger.info(f"Payment status created successfully with ID {new_payment_status.id}")
        return new_payment_status
    except IntegrityError as e:
        logger.error(f"IntegrityError while creating payment status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment status with this name already exists"
        )
    except Exception as e:
        logger.error(f"Error creating payment status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating payment status"
        )


@router.put("/{payment_status_id}", response_model=PaymentStatusResponse)
async def update_payment_status(
    payment_status_id: int,
    payment_status: PaymentStatusUpdate,
    session: AsyncSession = Depends(get_db),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Обновить статус оплаты.
    """
    existing_status = await PaymentStatusModel.get_by_id(session, payment_status_id)
    if not existing_status:
        logger.warning(f"Payment status with ID {payment_status_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment status not found"
        )
    
    logger.info(f"Admin (user ID {admin_user.get('user_id')}) updating payment status with ID {payment_status_id}: {payment_status}")
    
    try:
        updated_status = await PaymentStatusModel.update(session, payment_status_id, payment_status)
        logger.info(f"Payment status updated successfully: {updated_status.id}")
        return updated_status
    except IntegrityError as e:
        logger.error(f"IntegrityError while updating payment status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment status with this name already exists"
        )
    except Exception as e:
        logger.error(f"Error updating payment status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating payment status"
        )


@router.delete("/{payment_status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_status(
    payment_status_id: int,
    session: AsyncSession = Depends(get_db),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Удалить статус оплаты.
    """
    existing_status = await PaymentStatusModel.get_by_id(session, payment_status_id)
    if not existing_status:
        logger.warning(f"Payment status with ID {payment_status_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment status not found"
        )
    
    logger.info(f"Admin (user ID {admin_user.get('user_id')}) deleting payment status with ID {payment_status_id}")
    
    try:
        # Проверка, используется ли статус в заказах
        if await PaymentStatusModel.is_used_in_orders(session, payment_status_id):
            logger.warning(f"Cannot delete payment status with ID {payment_status_id} because it is used in orders")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete payment status that is used in orders"
            )
        
        await PaymentStatusModel.delete(session, payment_status_id)
        logger.info(f"Payment status with ID {payment_status_id} deleted successfully")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment status: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting payment status"
        ) 