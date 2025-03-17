from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional

from auth import get_current_user

import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_router")

# Создание роутера
router = APIRouter(
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

@router.get('/auth-check')
async def auth_check(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Проверка аутентификации пользователя.
    Возвращает информацию о текущем пользователе, если он аутентифицирован.
    Если пользователь не аутентифицирован, возвращает {"authenticated": false}.
    """
    if current_user:
        return {
            "authenticated": True,
            "user": current_user
        }
    return {"authenticated": False}
