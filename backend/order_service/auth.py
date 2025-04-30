"""Утилиты аутентификации и авторизации для сервиса заказов."""

import logging
import pathlib
import os
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from dotenv import load_dotenv

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_auth")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info("Загружаем .env из %s", env_file)
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    logger.info("Загружаем .env из %s", parent_env_file)
    load_dotenv(dotenv_path=parent_env_file)
else:
    logger.warning("Файл .env не найден!")

# Константы для JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")  # Значение по умолчанию для тестирования
ALGORITHM = "HS256"

logger.info("Загружена конфигурация JWT. SECRET_KEY: %s...", SECRET_KEY[:5])

# Схема авторизации через OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Класс пользователя для хранения данных из токена
class User:
    """Класс для хранения данных пользователя из JWT токена."""
    def __init__(self, id: int, is_admin: bool = False, is_super_admin: bool = False, is_active: bool = True):
        self.id = id
        self.is_admin = is_admin
        self.is_super_admin = is_super_admin
        self.is_active = is_active

async def get_token_from_cookie_or_header(
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
    logger.debug("OAuth token: %s", token)
    logger.debug("Cookie token: %s", access_token)
    logger.debug("Header Authorization: %s", authorization)
    
    # Приоритет токенов: сначала OAuth2, затем Cookie, потом Header
    if token:
        return token
        
    if access_token:
        return access_token
        
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
    
    return None

# Зависимость для получения текущего пользователя
async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """Получает текущего пользователя из JWT токена в cookie или заголовке Authorization.
    
    Args:
        request: FastAPI Request объект
        access_token: JWT токен из cookie
        authorization: JWT токен из заголовка Authorization
        
    Returns:
        User объект или None если токен невалидный или отсутствует
    """
    logger.info("Запрос авторизации: %s %s", request.method, request.url.path)
    
    # Если нет куки-токена, проверяем заголовок Authorization
    if not access_token and authorization:
        if authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
            logger.info("Токен получен из заголовка Authorization: %s...", access_token[:20])
        else:
            logger.warning("Заголовок Authorization не содержит Bearer токен")
    
    if not access_token:
        logger.warning("Токен не найден ни в cookie, ни в заголовке Authorization")
        return None
    
    try:
        logger.info("Попытка декодирования токена: %s...", access_token[:20])
        logger.info("Используемый SECRET_KEY: %s", SECRET_KEY)
        
        # Игнорируем проверку срока действия токена (для отладки)
        # ПРИМЕЧАНИЕ: В продакшене нужно убрать options и использовать стандартную проверку
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False}  # Отключаем проверку срока действия
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("В токене отсутствует sub с ID пользователя")
            return None
        
        # Добавляем проверку ролей из токена
        is_admin = payload.get("is_admin", False)
        is_super_admin = payload.get("is_super_admin", False)
        is_active = payload.get("is_active", True)
        
        logger.info("Токен декодирован успешно: user_id=%s, is_admin=%s, is_super_admin=%s", user_id, is_admin, is_super_admin)
        
        return User(
            id=int(user_id),
            is_admin=is_admin,
            is_super_admin=is_super_admin,
            is_active=is_active
        )
    except jwt.InvalidSignatureError:
        logger.error("Ошибка декодирования JWT: Неверная подпись токена")
        logger.error("Используемый SECRET_KEY: %s", SECRET_KEY)
        return None
    except jwt.ExpiredSignatureError:
        # Для отладки попробуем декодировать токен еще раз без проверки срока действия
        logger.warning("Токен просрочен, попытка декодирования без проверки срока действия")
        try:
            payload = jwt.decode(
                access_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": False}
            )
            user_id = payload.get("sub")
            if user_id is None:
                return None
                
            is_admin = payload.get("is_admin", False)
            is_super_admin = payload.get("is_super_admin", False)
            is_active = payload.get("is_active", True)
            
            logger.info("Просроченный токен успешно декодирован: user_id=%s", user_id)
            
            return User(
                id=int(user_id), 
                is_admin=is_admin, 
                is_super_admin=is_super_admin,
                is_active=is_active
            )
        except (jwt.InvalidSignatureError, jwt.DecodeError, jwt.PyJWTError) as e:
            logger.error("Не удалось декодировать просроченный токен: %s", e)
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
