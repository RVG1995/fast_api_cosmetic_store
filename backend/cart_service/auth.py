"""Утилиты аутентификации и авторизации для сервиса корзины."""

import logging
import uuid
from typing import Optional, Annotated, Dict, Any
import httpx
import json
import asyncio
import os

from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from dependencies import _get_service_token
from cache import cache_delete
from sqlalchemy.exc import SQLAlchemyError
from config import settings

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_auth")

# Константы для JWT из конфигурации
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM



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

async def get_session_id(
    session: Optional[str] = Cookie(None, alias="cart_session_id"),
    request: Request = None,
    session_id_param: Optional[str] = None
) -> str:
    """
    Получает ID сессии из куки, параметра или создаёт новый
    
    Приоритет:
    1. Значение из cookie
    2. Значение из параметра запроса
    3. Генерация нового ID
    """
    # Логируем источники session_id для отладки
    logger.debug("get_session_id: cookie=%s, param=%s", session, session_id_param)
    
    # Если session_id есть в cookie, используем его
    if session:
        logger.debug("Используем session_id из cookie: %s", session)
        return session
        
    # Если передан параметр session_id_param, используем его
    if session_id_param:
        logger.debug("Используем session_id из параметра: %s", session_id_param)
        return session_id_param
    
    # Пытаемся получить session_id из query параметров запроса, если request доступен
    if request and request.query_params.get("session_id"):
        session_id_from_query = request.query_params.get("session_id")
        logger.debug("Используем session_id из query параметра: %s", session_id_from_query)
        return session_id_from_query
    
    # Создаем новый ID сессии, если его нет
    session = str(uuid.uuid4())
    logger.info("Создан новый session_id: %s", session)
    
    return session

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
    """
    Получает текущего пользователя из JWT токена.
    
    Args:
        request: Объект запроса FastAPI
        access_token: JWT токен из cookie
        authorization: JWT токен из заголовка Authorization
        
    Returns:
        Optional[User]: Объект пользователя или None, если токен невалиден
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
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
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
        logger.error("Ошибка декодирования JWT: Токен просрочен")
        return None
    except jwt.DecodeError:
        logger.error("Ошибка декодирования JWT: Невозможно декодировать токен")
        return None
    except jwt.PyJWTError as e:
        logger.error("Ошибка декодирования JWT: %s, тип: %s", e, type(e).__name__)
        return None

async def get_current_admin_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    """
    Проверяет, что текущий пользователь является администратором,
    Если пользователь не аутентифицирован или не имеет прав администратора, 
    выбрасывает исключение 401 Unauthorized или 403 Forbidden.
    
    Args:
        current_user: Текущий пользователь, полученный из токена
         
    Returns:
        User: Пользователь с админ-правами
    """
    # Проверяем, что пользователь аутентифицирован
    if not current_user:
        logger.warning("get_current_admin_user: Пользователь не аутентифицирован")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
         
    # Проверяем, что пользователь имеет права администратора или суперадминистратора
    if not current_user.is_admin and not current_user.is_super_admin:
        logger.warning("get_current_admin_user: Пользователь %s не имеет прав администратора", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции",
        )
        
    logger.info("get_current_admin_user: Пользователь %s успешно авторизован как администратор", current_user.id)
    return current_user


async def get_user_info(user_id: int) -> Dict[str, Any]:
    """
    Получает информацию о пользователе из сервиса авторизации
    """
    try:
        auth_service_url = os.environ.get("AUTH_SERVICE_URL", "http://localhost:8000")        
        logger.info("Запрос информации о пользователе %d по URL: %s/admin/users/%d", user_id, auth_service_url, user_id)
        backoffs = [0.5, 1, 2]        
        async with httpx.AsyncClient() as client:
            total = len(backoffs)
            for attempt, delay in enumerate(backoffs, start=1):
                logger.info("get_user_info: attempt %d/%d for user %d", attempt, total, user_id)
                token = await _get_service_token()
                headers = {"Authorization": f"Bearer {token}"}
                try:
                    response = await client.get(
                        f"{auth_service_url}/admin/users/{user_id}",
                        headers=headers,
                        timeout=5.0
                    )
                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    logger.error("get_user_info: network error on attempt %d: %s", attempt, exc)
                    if attempt < total:
                        await asyncio.sleep(delay)
                        continue
                    break
                logger.info("get_user_info: status=%d", response.status_code)
                if response.status_code == 200:
                    try:
                        user_data = response.json()
                    except (json.JSONDecodeError, ValueError) as parse_exc:
                        logger.error("get_user_info: JSON parse error: %s", parse_exc)
                        return {}
                    if "first_name" not in user_data or "last_name" not in user_data:
                        logger.warning("get_user_info: missing name fields in response: %s", user_data)
                    return user_data
                if response.status_code == 404:
                    logger.warning("get_user_info: 404 Not Found on attempt %d, returning empty response", attempt)
                    return {}
                if response.status_code == 401:
                    logger.warning("get_user_info: 401 Unauthorized on attempt %d, clearing cache and retry", attempt)
                    await cache_delete("service_token")
                    if attempt < total:
                        await asyncio.sleep(delay)
                        continue
                    break
                logger.error("get_user_info: unexpected status %d, body=%s", response.status_code, response.text)
                return {}
            logger.error("get_user_info: completing all attempts, returning empty response")
            return {}
    except (SQLAlchemyError, HTTPException, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Ошибка при запросе информации о пользователе %d: %s", user_id, str(e))
        return {}