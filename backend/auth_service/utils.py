from passlib.context import CryptContext
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header,Cookie
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import os
import jwt
from jwt.exceptions import PyJWTError
import logging
import httpx
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# Получение настроек JWT из переменных окружения
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Настройка для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

async def get_password_hash(password: str) -> str:
    """Хеширует пароль"""
    return pwd_context.hash(password)

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля хешу"""
    return pwd_context.verify(plain_password, hashed_password)


async def verify_service_jwt(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> bool:
    """Проверяет JWT токен с scope 'service'"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True
