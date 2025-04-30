"""Модуль для административных эндпоинтов аутентификации и управления пользователями."""

import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserModel
from schema import AdminUserReadShema
from auth_utils import get_admin_user, get_super_admin_user
from database import get_session
from utils import verify_service_jwt
# Получаем сервисный ключ из переменных окружения
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")

router = APIRouter(prefix="/admin", tags=["admin"])

async def verify_service_key(service_key: str = Header(None, alias="service-key")):
    """Проверяет сервисный ключ для межсервисного взаимодействия"""
    if not service_key or service_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует или неверный сервисный ключ"
        )
    return True

@router.get("/users", response_model=List[AdminUserReadShema], dependencies=[Depends(get_admin_user)])
async def get_all_users(
    session: AsyncSession = Depends(get_session)
):
    """Получить список всех пользователей (только для админов)"""
    stmt = select(UserModel)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return users

@router.patch("/users/{user_id}/activate", dependencies=[Depends(get_admin_user)])
async def admin_activate_user(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Активировать пользователя (только для админов)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.is_active = True
    user.activation_token = None
    await session.commit()
    return {"message": f"Пользователь {user.email} активирован"}

@router.patch("/users/{user_id}/make-admin", dependencies=[Depends(get_super_admin_user)])
async def make_user_admin(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Предоставить пользователю права администратора (только для суперадмина)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.is_admin = True
    await session.commit()
    return {"message": f"Пользователю {user.email} предоставлены права администратора"}

@router.patch("/users/{user_id}/remove-admin", dependencies=[Depends(get_super_admin_user)])
async def remove_admin_rights(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Отозвать права администратора у пользователя (только для суперадмина)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем, что пользователь не является суперадмином
    if user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно отозвать права администратора у суперадминистратора"
        )
    
    user.is_admin = False
    await session.commit()
    return {"message": f"У пользователя {user.email} отозваны права администратора"}

@router.delete("/users/{user_id}", dependencies=[Depends(get_super_admin_user)])
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Удалить пользователя (только для суперадмина)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    await session.delete(user)
    await session.commit()
    return {"message": f"Пользователь {user.email} удален"}

@router.get("/check-access", dependencies=[Depends(get_admin_user)])
async def check_admin_access():
    """Эндпоинт для проверки прав администратора"""
    return {"status": "success", "message": "У вас есть права администратора"}

@router.get("/check-super-access", dependencies=[Depends(get_super_admin_user)])
async def check_super_admin_access():
    """Эндпоинт для проверки прав суперадминистратора"""
    return {"status": "success", "message": "У вас есть права суперадминистратора"}

@router.get("/users/{user_id}", response_model=AdminUserReadShema, dependencies=[Depends(verify_service_jwt)])
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Получить информацию о конкретном пользователе по ID (для межсервисных запросов)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return user
