from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from database import get_db
from dependencies import get_admin_user
from models import BoxberryStatusFunnelModel, OrderStatusModel
from schemas import BoxberryStatusFunnelCreate, BoxberryStatusFunnelUpdate, BoxberryStatusFunnelResponse, OrderStatusResponse
from services import (
    get_boxberry_funnel_all, get_boxberry_funnel_by_id,
    create_boxberry_funnel, update_boxberry_funnel, delete_boxberry_funnel
)
from config import settings
from sqlalchemy.exc import IntegrityError

router = APIRouter(
    prefix="/boxberry-funnel",
    tags=["boxberry_funnel"],
    dependencies=[Depends(get_admin_user)],
)

@router.get("", response_model=List[BoxberryStatusFunnelResponse])
async def list_boxberry_funnel(session: AsyncSession = Depends(get_db)):
    funnels = await get_boxberry_funnel_all(session)
    return funnels

@router.get("/boxberry-statuses", response_model=List[dict])
async def get_boxberry_statuses():
    """Получить список Boxberry статусов (код+имя) из конфига."""
    return [
        {"code": int(code), "name": name}
        for code, name in settings.BOXBERRY_STATUSES.items()
    ]

@router.get("/{funnel_id}", response_model=BoxberryStatusFunnelResponse)
async def get_boxberry_funnel_view(funnel_id: int, session: AsyncSession = Depends(get_db)):
    funnel = await get_boxberry_funnel_by_id(session, funnel_id)
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    funnel.order_status = await session.get(OrderStatusModel, funnel.order_status_id)
    return funnel

@router.post("", response_model=BoxberryStatusFunnelResponse, status_code=status.HTTP_201_CREATED)
async def create_boxberry_funnel_view(data: BoxberryStatusFunnelCreate, session: AsyncSession = Depends(get_db)):
    try:
        funnel = await create_boxberry_funnel(session, data)
        funnel.order_status = await session.get(OrderStatusModel, funnel.order_status_id)
        return funnel
    except IntegrityError as e:
        await session.rollback()
        if 'unique' in str(e.orig).lower() or 'duplicate' in str(e.orig).lower():
            raise HTTPException(status_code=409, detail="Такое правило уже существует (дублирующий код Boxberry)")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении правила")

@router.put("/{funnel_id}", response_model=BoxberryStatusFunnelResponse)
async def update_boxberry_funnel_view(funnel_id: int, data: BoxberryStatusFunnelUpdate, session: AsyncSession = Depends(get_db)):
    try:
        funnel = await update_boxberry_funnel(session, funnel_id, data)
        if not funnel:
            raise HTTPException(status_code=404, detail="Маппинг не найден")
        funnel.order_status = await session.get(OrderStatusModel, funnel.order_status_id)
        return funnel
    except IntegrityError as e:
        await session.rollback()
        if 'unique' in str(e.orig).lower() or 'duplicate' in str(e.orig).lower():
            raise HTTPException(status_code=409, detail="Такое правило уже существует (дублирующий код Boxberry)")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении правила")

@router.delete("/{funnel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_boxberry_funnel_view(funnel_id: int, session: AsyncSession = Depends(get_db)):
    ok = await delete_boxberry_funnel(session, funnel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Маппинг не найден")
    return None 