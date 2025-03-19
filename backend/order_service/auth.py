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

# Зависимость для получения текущего пользователя
async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    logger.info(f"Запрос авторизации: {request.method} {request.url.path}")
    
    # Если нет куки-токена, проверяем заголовок Authorization
    if not access_token and authorization:
        if authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
            logger.info(f"Токен получен из заголовка Authorization: {access_token[:20]}...")
        else:
            logger.warning("Заголовок Authorization не содержит Bearer токен")
    
    if not access_token:
        logger.warning("Токен не найден ни в cookie, ни в заголовке Authorization")
        return None
    
    try:
        logger.info(f"Попытка декодирования токена: {access_token[:20]}...")
        logger.info(f"Используемый SECRET_KEY: {SECRET_KEY}")
        
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
        
        logger.info(f"Токен декодирован успешно: user_id={user_id}, is_admin={is_admin}, is_super_admin={is_super_admin}")
        
        return User(
            id=int(user_id), 
            is_admin=is_admin, 
            is_super_admin=is_super_admin,
            is_active=is_active
        )
    except jwt.InvalidSignatureError:
        logger.error("Ошибка декодирования JWT: Неверная подпись токена")
        logger.error(f"Используемый SECRET_KEY: {SECRET_KEY}")
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
            
            logger.info(f"Просроченный токен успешно декодирован: user_id={user_id}")
            
            return User(
                id=int(user_id), 
                is_admin=is_admin, 
                is_super_admin=is_super_admin,
                is_active=is_active
            )
        except Exception as e:
            logger.error(f"Не удалось декодировать просроченный токен: {e}")
            return None
    except jwt.DecodeError:
        logger.error("Ошибка декодирования JWT: Невозможно декодировать токен")
        return None
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка декодирования JWT: {e}, тип: {type(e).__name__}")
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