from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserModel
from schema import AdminUserReadShema
from router import get_current_user
from database import get_session

router = APIRouter(prefix="/admin", tags=["admin"])

async def get_admin_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Проверяет, что текущий пользователь - администратор"""
    if not (current_user.is_admin or current_user.is_super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа",
        )
    return current_user

async def get_super_admin_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Проверяет, что текущий пользователь - суперадминистратор"""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа",
        )
    return current_user

@router.get("/users", response_model=List[AdminUserReadShema])
async def get_all_users(
    session: AsyncSession = Depends(get_session),
    _: UserModel = Depends(get_admin_user)  # Проверка прав администратора
):
    """Получить список всех пользователей (только для админов)"""
    stmt = select(UserModel)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return users

@router.patch("/users/{user_id}/activate")
async def admin_activate_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: UserModel = Depends(get_admin_user)
):
    """Активировать пользователя (только для админов)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.is_active = True
    user.activation_token = None
    await session.commit()
    return {"message": f"Пользователь {user.email} активирован"}

@router.patch("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: UserModel = Depends(get_super_admin_user)  # Только суперадмин
):
    """Предоставить пользователю права администратора (только для суперадмина)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.is_admin = True
    await session.commit()
    return {"message": f"Пользователю {user.email} предоставлены права администратора"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: UserModel = Depends(get_super_admin_user)  # Только суперадмин
):
    """Удалить пользователя (только для суперадмина)"""
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    await session.delete(user)
    await session.commit()
    return {"message": f"Пользователь {user.email} удален"}

@router.get("/check-access")
async def check_admin_access(
    admin_user: UserModel = Depends(get_admin_user)
):
    """Эндпоинт для проверки прав администратора"""
    return {"status": "success", "message": "У вас есть права администратора"}

@router.get("/check-super-access")
async def check_super_admin_access(
    super_admin_user: UserModel = Depends(get_super_admin_user)
):
    """Эндпоинт для проверки прав суперадминистратора"""
    return {"status": "success", "message": "У вас есть права суперадминистратора"}
