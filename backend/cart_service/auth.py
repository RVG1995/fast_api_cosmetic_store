from fastapi import Depends, HTTPException, status, Cookie, Request, Header
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Annotated, List
import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import pathlib
import uuid

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_auth")

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

# Константы для JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")  # Значение по умолчанию для тестирования
ALGORITHM = "HS256"

# Сервисный API-ключ
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")

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
    logger.debug(f"get_session_id: cookie={session}, param={session_id_param}")
    
    # Если session_id есть в cookie, используем его
    if session:
        logger.debug(f"Используем session_id из cookie: {session}")
        return session
        
    # Если передан параметр session_id_param, используем его
    if session_id_param:
        logger.debug(f"Используем session_id из параметра: {session_id_param}")
        return session_id_param
    
    # Пытаемся получить session_id из query параметров запроса, если request доступен
    if request and request.query_params.get("session_id"):
        session_id_from_query = request.query_params.get("session_id")
        logger.debug(f"Используем session_id из query параметра: {session_id_from_query}")
        return session_id_from_query
    
    # Создаем новый ID сессии, если его нет
    session = str(uuid.uuid4())
    logger.info(f"Создан новый session_id: {session}")
    
    return session

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

async def get_current_admin_user(
    request: Request,
    token: Annotated[Optional[str], Depends(get_token_from_cookie_or_header)],
    service_key: Optional[str] = Header(None, alias="service-key")
) -> Optional[User]:
    """
    Проверяет, что текущий пользователь является администратором,
    или что запрос содержит правильный сервисный ключ.
    
    Если пользователь не аутентифицирован и сервисный ключ неверный, 
    выбрасывает исключение 401 Unauthorized.
    
    Args:
        request: Объект запроса
        token: JWT токен
        service_key: Секретный ключ для межсервисного взаимодействия
        
    Returns:
        Optional[User]: Пользователь с админ-правами, или None для сервисного ключа
    """
    # Проверка сервисного ключа для межсервисного взаимодействия
    if service_key and service_key == INTERNAL_SERVICE_KEY:
        logger.info("Запрос авторизован через сервисный ключ")
        # Для сервисного запроса возвращаем None (означает, что авторизация прошла через ключ)
        return None
    
    # Если нет сервисного ключа, проверяем наличие пользователя с правами админа
    access_token = None
    authorization = None
    
    # Получаем токен из cookie, если есть
    for cookie in request.cookies:
        if cookie == "access_token":
            access_token = request.cookies[cookie]
            break
    
    # Получаем токен из заголовка Authorization, если есть
    if "authorization" in request.headers:
        authorization = request.headers["authorization"]
    
    user = await get_current_user(request, access_token, authorization)
    
    if not user:
        logger.warning("Отсутствует авторизованный пользователь и сервисный ключ")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация или сервисный ключ",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Проверяем, что пользователь имеет права администратора
    if not (user.is_admin or user.is_super_admin):
        logger.warning(f"Пользователь {user.id} не имеет прав администратора")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    logger.info(f"Администратор {user.id} успешно авторизован")
    return user 