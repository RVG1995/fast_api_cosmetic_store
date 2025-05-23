"""Модуль для авторизации и проверки JWT токенов в product_service."""
import logging
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
import jwt

from config import settings

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_auth")

# Константы для JWT из настроек
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

logger.info("Загружена конфигурация JWT. SECRET_KEY: %s...", SECRET_KEY[:5])

# Схема авторизации через OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Класс пользователя для хранения данных из токена
class User:
    """Модель пользователя, извлечённого из JWT токена."""
    def __init__(self, id: int, is_admin: bool = False, is_super_admin: bool = False, is_active: bool = True):
        self.id = id
        self.is_admin = is_admin
        self.is_super_admin = is_super_admin
        self.is_active = is_active
    
    def has_admin_rights(self):
        """Проверка наличия прав администратора"""
        return self.is_admin or self.is_super_admin

# Зависимость для получения текущего пользователя
async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """Получает текущего пользователя из JWT токена."""
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
        # Если это JWT сервисного доступа, возвращаем None, без попытки parsing sub в int
        if payload.get("scope") == "service":
            logger.info("get_current_user: service JWT detected, returning None for user")
            return None
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

# Зависимость для проверки прав администратора
def require_admin(user: Annotated[Optional[User], Depends(get_current_user)]):
    """Проверяет наличие прав администратора у пользователя."""
    if not user:
        logger.warning("Доступ запрещен: пользователь не авторизован")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.has_admin_rights():
        logger.warning("Доступ запрещен: пользователь ID %s не имеет прав администратора", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции",
        )
    
    logger.info("Доступ разрешен: пользователь ID %s имеет права администратора", user.id)
    return user
