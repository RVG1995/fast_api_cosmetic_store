from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Annotated
import jwt
import os
from dotenv import load_dotenv
import logging
import pathlib

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_auth")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info(f"Загружаем .env из {env_file}")
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    logger.info(f"Загружаем .env из {parent_env_file}")
    load_dotenv(dotenv_path=parent_env_file)
else:
    logger.warning("Файл .env не найден!")

# Константы для JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")  # Значение по умолчанию для тестирования
ALGORITHM = "HS256"

logger.info(f"Загружена конфигурация JWT. SECRET_KEY: {SECRET_KEY[:5]}...")

# Схема авторизации через OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Класс пользователя для хранения данных из токена
class User:
    def __init__(self, id: int, is_admin: bool = False, is_super_admin: bool = False, is_active: bool = True):
        self.id = id
        self.is_admin = is_admin
        self.is_super_admin = is_super_admin
        self.is_active = is_active

async def get_token_from_cookie_or_header(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)] = None,
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Пытается получить JWT токен из разных источников:
    1. OAuth2 Bearer Token
    2. Cookie 'access_token'
    3. Header 'Authorization' в формате Bearer
    """
    # Логируем все возможные источники токена
    logger.debug(f"OAuth token: {token}")
    logger.debug(f"Cookie token: {access_token}")
    logger.debug(f"Header Authorization: {authorization}")
    
    # Приоритет токенов: сначала OAuth2, затем Cookie, потом Header
    if token:
        return token
        
    if access_token:
        return access_token
        
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
    
    return None

async def get_current_user(
    token: Annotated[Optional[str], Depends(get_token_from_cookie_or_header)]
) -> Optional[User]:
    """
    Проверяет JWT токен и возвращает информацию о пользователе, если токен валидный.
    Если токен отсутствует или невалидный, возвращает None.
    """
    if not token:
        logger.info("Токен не предоставлен")
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("Токен не содержит поле 'sub'")
            return None
            
        # Извлекаем информацию о правах пользователя
        is_admin = payload.get("is_admin", False)
        is_super_admin = payload.get("is_super_admin", False)
        is_active = payload.get("is_active", True)
        
        logger.info(f"Пользователь {user_id} успешно аутентифицирован (admin={is_admin}, super_admin={is_super_admin})")
        return User(id=int(user_id), is_admin=is_admin, is_super_admin=is_super_admin, is_active=is_active)
    except jwt.PyJWTError as e:
        logger.warning(f"Ошибка проверки JWT: {str(e)}")
        return None

def check_admin_access(user: Optional[User] = Depends(get_current_user)):
    """Проверяет, что пользователь аутентифицирован и имеет права администратора"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    if not (user.is_admin or user.is_super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуются права администратора"
        )
    return user

def check_super_admin_access(user: Optional[User] = Depends(get_current_user)):
    """Проверяет, что пользователь аутентифицирован и имеет права супер-администратора"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуются права супер-администратора"
        )
    return user

def check_authenticated(user: Optional[User] = Depends(get_current_user)):
    """Проверяет, что пользователь аутентифицирован"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация"
        )
    return user 