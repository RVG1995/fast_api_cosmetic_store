from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
import logging

from database import get_db
from models import ShippingAddressModel, BillingAddressModel
from schemas import (
    ShippingAddressCreate, BillingAddressCreate, 
    ShippingAddressResponse, BillingAddressResponse,
    AddressUpdate
)
from dependencies import get_current_user, get_admin_user

# Настройка логирования
logger = logging.getLogger("address_router")

# Создание роутера для адресов доставки
shipping_router = APIRouter(
    prefix="/shipping-addresses",
    tags=["shipping_addresses"],
    responses={404: {"description": "Not found"}},
)

# Создание роутера для адресов для выставления счетов
billing_router = APIRouter(
    prefix="/api/billing-addresses",
    tags=["billing_addresses"],
    responses={404: {"description": "Not found"}},
)

# Маршруты для адресов доставки
@shipping_router.get("", response_model=List[ShippingAddressResponse])
async def list_shipping_addresses(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка адресов доставки текущего пользователя.
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
        # Получаем адреса доставки пользователя
        query = select(ShippingAddressModel).filter(ShippingAddressModel.user_id == user_id)
        result = await session.execute(query)
        addresses = result.scalars().all()
        
        return [ShippingAddressResponse.from_orm(address) for address in addresses]
    except Exception as e:
        logger.error(f"Ошибка при получении списка адресов доставки: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка адресов доставки",
        )

@shipping_router.get("/{address_id}", response_model=ShippingAddressResponse)
async def get_shipping_address(
    address_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации об адресе доставки по ID.
    
    - **address_id**: ID адреса доставки
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем адрес доставки
        query = select(ShippingAddressModel).filter(ShippingAddressModel.id == address_id)
        if not is_admin:
            query = query.filter(ShippingAddressModel.user_id == user_id)
        
        result = await session.execute(query)
        address = result.scalars().first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Адрес доставки с ID {address_id} не найден",
            )
        
        return ShippingAddressResponse.from_orm(address)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации об адресе доставки: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации об адресе доставки",
        )

@shipping_router.post("", response_model=ShippingAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_shipping_address(
    address_data: ShippingAddressCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание нового адреса доставки.
    
    - **address_data**: Данные для создания адреса доставки
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
        # Если адрес помечен как адрес по умолчанию, сбрасываем флаг у других адресов
        if address_data.is_default:
            update_query = update(ShippingAddressModel).where(
                ShippingAddressModel.user_id == user_id
            ).values(is_default=False)
            await session.execute(update_query)
        
        # Создаем новый адрес доставки
        address = ShippingAddressModel(
            user_id=user_id,
            full_name=address_data.full_name,
            address_line1=address_data.address_line1,
            address_line2=address_data.address_line2,
            city=address_data.city,
            state=address_data.state,
            postal_code=address_data.postal_code,
            country=address_data.country,
            phone_number=address_data.phone_number,
            is_default=address_data.is_default
        )
        session.add(address)
        await session.commit()
        await session.refresh(address)
        
        return ShippingAddressResponse.from_orm(address)
    except Exception as e:
        logger.error(f"Ошибка при создании адреса доставки: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании адреса доставки",
        )

@shipping_router.put("/{address_id}", response_model=ShippingAddressResponse)
async def update_shipping_address(
    address_id: int = Path(..., ge=1),
    address_data: AddressUpdate = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление информации об адресе доставки.
    
    - **address_id**: ID адреса доставки
    - **address_data**: Данные для обновления
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем адрес доставки
        query = select(ShippingAddressModel).filter(ShippingAddressModel.id == address_id)
        if not is_admin:
            query = query.filter(ShippingAddressModel.user_id == user_id)
        
        result = await session.execute(query)
        address = result.scalars().first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Адрес доставки с ID {address_id} не найден",
            )
        
        # Если адрес помечен как адрес по умолчанию, сбрасываем флаг у других адресов
        if address_data.is_default:
            update_query = update(ShippingAddressModel).where(
                ShippingAddressModel.user_id == address.user_id,
                ShippingAddressModel.id != address_id
            ).values(is_default=False)
            await session.execute(update_query)
        
        # Обновляем данные адреса доставки
        if address_data.full_name is not None:
            address.full_name = address_data.full_name
        
        if address_data.address_line1 is not None:
            address.address_line1 = address_data.address_line1
        
        if address_data.address_line2 is not None:
            address.address_line2 = address_data.address_line2
        
        if address_data.city is not None:
            address.city = address_data.city
        
        if address_data.state is not None:
            address.state = address_data.state
        
        if address_data.postal_code is not None:
            address.postal_code = address_data.postal_code
        
        if address_data.country is not None:
            address.country = address_data.country
        
        if address_data.phone_number is not None:
            address.phone_number = address_data.phone_number
        
        if address_data.is_default is not None:
            address.is_default = address_data.is_default
        
        await session.commit()
        await session.refresh(address)
        
        return ShippingAddressResponse.from_orm(address)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении адреса доставки: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении адреса доставки",
        )

@shipping_router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipping_address(
    address_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Удаление адреса доставки.
    
    - **address_id**: ID адреса доставки
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем адрес доставки
        query = select(ShippingAddressModel).filter(ShippingAddressModel.id == address_id)
        if not is_admin:
            query = query.filter(ShippingAddressModel.user_id == user_id)
        
        result = await session.execute(query)
        address = result.scalars().first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Адрес доставки с ID {address_id} не найден",
            )
        
        # Удаляем адрес доставки
        await session.delete(address)
        
        # Если удаленный адрес был адресом по умолчанию, устанавливаем новый адрес по умолчанию
        if address.is_default:
            # Получаем первый доступный адрес пользователя
            query = select(ShippingAddressModel).filter(
                ShippingAddressModel.user_id == address.user_id,
                ShippingAddressModel.id != address_id
            ).limit(1)
            result = await session.execute(query)
            new_default_address = result.scalars().first()
            
            if new_default_address:
                new_default_address.is_default = True
        
        await session.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении адреса доставки: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении адреса доставки",
        )

# Маршруты для адресов для выставления счетов
@billing_router.get("", response_model=List[BillingAddressResponse])
async def list_billing_addresses(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка адресов для выставления счетов текущего пользователя.
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
        # Получаем адреса для выставления счетов пользователя
        query = select(BillingAddressModel).filter(BillingAddressModel.user_id == user_id)
        result = await session.execute(query)
        addresses = result.scalars().all()
        
        return [BillingAddressResponse.from_orm(address) for address in addresses]
    except Exception as e:
        logger.error(f"Ошибка при получении списка адресов для выставления счетов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка адресов для выставления счетов",
        )

@billing_router.get("/{address_id}", response_model=BillingAddressResponse)
async def get_billing_address(
    address_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации об адресе для выставления счетов по ID.
    
    - **address_id**: ID адреса для выставления счетов
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем адрес для выставления счетов
        query = select(BillingAddressModel).filter(BillingAddressModel.id == address_id)
        if not is_admin:
            query = query.filter(BillingAddressModel.user_id == user_id)
        
        result = await session.execute(query)
        address = result.scalars().first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Адрес для выставления счетов с ID {address_id} не найден",
            )
        
        return BillingAddressResponse.from_orm(address)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации об адресе для выставления счетов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации об адресе для выставления счетов",
        )

@billing_router.post("", response_model=BillingAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_address(
    address_data: BillingAddressCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание нового адреса для выставления счетов.
    
    - **address_data**: Данные для создания адреса для выставления счетов
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
        # Если адрес помечен как адрес по умолчанию, сбрасываем флаг у других адресов
        if address_data.is_default:
            update_query = update(BillingAddressModel).where(
                BillingAddressModel.user_id == user_id
            ).values(is_default=False)
            await session.execute(update_query)
        
        # Создаем новый адрес для выставления счетов
        address = BillingAddressModel(
            user_id=user_id,
            full_name=address_data.full_name,
            address_line1=address_data.address_line1,
            address_line2=address_data.address_line2,
            city=address_data.city,
            state=address_data.state,
            postal_code=address_data.postal_code,
            country=address_data.country,
            phone_number=address_data.phone_number,
            is_default=address_data.is_default
        )
        session.add(address)
        await session.commit()
        await session.refresh(address)
        
        return BillingAddressResponse.from_orm(address)
    except Exception as e:
        logger.error(f"Ошибка при создании адреса для выставления счетов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании адреса для выставления счетов",
        )

@billing_router.put("/{address_id}", response_model=BillingAddressResponse)
async def update_billing_address(
    address_id: int = Path(..., ge=1),
    address_data: AddressUpdate = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление информации об адресе для выставления счетов.
    
    - **address_id**: ID адреса для выставления счетов
    - **address_data**: Данные для обновления
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем адрес для выставления счетов
        query = select(BillingAddressModel).filter(BillingAddressModel.id == address_id)
        if not is_admin:
            query = query.filter(BillingAddressModel.user_id == user_id)
        
        result = await session.execute(query)
        address = result.scalars().first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Адрес для выставления счетов с ID {address_id} не найден",
            )
        
        # Если адрес помечен как адрес по умолчанию, сбрасываем флаг у других адресов
        if address_data.is_default:
            update_query = update(BillingAddressModel).where(
                BillingAddressModel.user_id == address.user_id,
                BillingAddressModel.id != address_id
            ).values(is_default=False)
            await session.execute(update_query)
        
        # Обновляем данные адреса для выставления счетов
        if address_data.full_name is not None:
            address.full_name = address_data.full_name
        
        if address_data.address_line1 is not None:
            address.address_line1 = address_data.address_line1
        
        if address_data.address_line2 is not None:
            address.address_line2 = address_data.address_line2
        
        if address_data.city is not None:
            address.city = address_data.city
        
        if address_data.state is not None:
            address.state = address_data.state
        
        if address_data.postal_code is not None:
            address.postal_code = address_data.postal_code
        
        if address_data.country is not None:
            address.country = address_data.country
        
        if address_data.phone_number is not None:
            address.phone_number = address_data.phone_number
        
        if address_data.is_default is not None:
            address.is_default = address_data.is_default
        
        await session.commit()
        await session.refresh(address)
        
        return BillingAddressResponse.from_orm(address)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении адреса для выставления счетов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении адреса для выставления счетов",
        )

@billing_router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_address(
    address_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Удаление адреса для выставления счетов.
    
    - **address_id**: ID адреса для выставления счетов
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем адрес для выставления счетов
        query = select(BillingAddressModel).filter(BillingAddressModel.id == address_id)
        if not is_admin:
            query = query.filter(BillingAddressModel.user_id == user_id)
        
        result = await session.execute(query)
        address = result.scalars().first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Адрес для выставления счетов с ID {address_id} не найден",
            )
        
        # Удаляем адрес для выставления счетов
        await session.delete(address)
        
        # Если удаленный адрес был адресом по умолчанию, устанавливаем новый адрес по умолчанию
        if address.is_default:
            # Получаем первый доступный адрес пользователя
            query = select(BillingAddressModel).filter(
                BillingAddressModel.user_id == address.user_id,
                BillingAddressModel.id != address_id
            ).limit(1)
            result = await session.execute(query)
            new_default_address = result.scalars().first()
            
            if new_default_address:
                new_default_address.is_default = True
        
        await session.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении адреса для выставления счетов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении адреса для выставления счетов",
        ) 