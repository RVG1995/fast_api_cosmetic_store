from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Annotated, List
import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import pathlib

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product_auth")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info(f"Загружаем .env из {env_file}")
    load_dotenv(dotenv_path=env_file)
    logger.info(f"Содержимое JWT_SECRET_KEY в .env: {os.getenv('JWT_SECRET_KEY', 'не найден')}")
elif parent_env_file.exists():
    logger.info(f"Загружаем .env из {parent_env_file}")
    load_dotenv(dotenv_path=parent_env_file)
    logger.info(f"Содержимое JWT_SECRET_KEY в родительском .env: {os.getenv('JWT_SECRET_KEY', 'не найден')}")
else:
    logger.warning("Файл .env не найден!")

# Константы для JWT - используем фиксированное значение для отладки
# SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_secret_key_here")
SECRET_KEY = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"  # Жестко закодированное значение для тестирования
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
    
    def has_admin_rights(self):
        """Проверка наличия прав администратора"""
        return self.is_admin or self.is_super_admin

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
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
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
        logger.error("Ошибка декодирования JWT: Токен просрочен")
        return None
    except jwt.DecodeError:
        logger.error("Ошибка декодирования JWT: Невозможно декодировать токен")
        return None
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка декодирования JWT: {e}, тип: {type(e).__name__}")
        return None

# Зависимость для проверки прав администратора
def require_admin(user: Annotated[Optional[User], Depends(get_current_user)]):
    if not user:
        logger.warning("Доступ запрещен: пользователь не авторизован")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.has_admin_rights():
        logger.warning(f"Доступ запрещен: пользователь ID {user.id} не имеет прав администратора")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции",
        )
    
    logger.info(f"Доступ разрешен: пользователь ID {user.id} имеет права администратора")
    return user 