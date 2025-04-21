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
from cache import get_cached_data, set_cached_data, redis_client
from datetime import datetime, timezone


from database import get_db
from schemas import OrderFilterParams
from product_api import get_product_api

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger("order_dependencies")

# Получение настроек JWT из переменных окружения
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# URL сервисов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://localhost:8002")


NOTIFICATION_SERVICE_URL = "http://localhost:8005"  # Адрес сервиса уведомлений
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")  # Адрес сервиса авторизации
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")  # устаревший, не используется при client_credentials

# Client credentials for service-to-service auth
SERVICE_CLIENTS_RAW = os.getenv("SERVICE_CLIENTS_RAW", "")
SERVICE_CLIENTS = {kv.split(":")[0]: kv.split(":")[1] for kv in SERVICE_CLIENTS_RAW.split(",") if ":" in kv}
SERVICE_CLIENT_ID = os.getenv("SERVICE_CLIENT_ID","orders")
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = int(os.getenv("SERVICE_TOKEN_EXPIRE_MINUTES", "30"))

ALGORITHM = os.getenv("ALGORITHM", "HS256")

bearer_scheme = HTTPBearer(auto_error=False)

async def _get_service_token():
    # try cache
    token = await get_cached_data("service_token")
    if token:
        return token
    # Получаем секрет из общего SERVICE_CLIENTS_RAW
    secret = SERVICE_CLIENTS.get(SERVICE_CLIENT_ID)
    if not secret:
        raise RuntimeError(f"Нет секрета для client_id={SERVICE_CLIENT_ID}")
    data = {"grant_type":"client_credentials","client_id":SERVICE_CLIENT_ID,"client_secret":secret}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AUTH_SERVICE_URL}/auth/token", data=data, timeout=5)
        r.raise_for_status()
        new_token = r.json().get("access_token")
    # cache with TTL from exp claim or default
    ttl = SERVICE_TOKEN_EXPIRE_MINUTES*60 - 30
    try:
        payload = jwt.decode(new_token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp:
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp() - 5), 1)
    except Exception:
        pass
    await set_cached_data("service_token", new_token, ttl)
    return new_token

async def verify_service_jwt(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> bool:
    """Проверяет JWT токен с scope 'service'"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True

# Схема OAuth2 для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Функция для проверки токена и получения данных пользователя
async def get_current_user(
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme),
    x_service_name: Optional[str] = Header(None),
    service_jwt: Optional[bool] = Depends(bearer_scheme)
)-> Optional[Dict[str, Any]]:
    logger.info(f"Получен токен из куки: {token}")
    logger.info(f"Получен токен из заголовка: {authorization}")

    actual_token = None
    
    # Если токен есть в куках, используем его
    if token:
        actual_token = token
        logger.info(f"Используем токен из куки: {token[:20]}...")
    # Если в куках нет, но есть в заголовке, используем его
    elif authorization:
        if authorization.startswith('Bearer '):
            actual_token = authorization[7:]
        else:
            actual_token = authorization
        logger.info(f"Используем токен из заголовка Authorization: {actual_token[:20]}...")
    
    # Если токен не найден, возвращаем None для анонимного доступа
    if actual_token is None:
        logger.info("Токен не найден, продолжаем с анонимным доступом")
        return None
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Проверяем, это сервисный JWT с параметром scope=service
    try:
        payload = jwt.decode(actual_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") == "service" and x_service_name:
            logger.info(f"Внутренний запрос от сервиса {x_service_name} авторизован через JWT")
            # Возвращаем специальные данные для внутреннего сервиса с повышенными правами
            return {
                "user_id": None,
                "is_admin": True,
                "is_super_admin": True,
                "is_service": True,
                "service_name": x_service_name,
                "token": actual_token
            }
    except Exception:
        # Если не сервисный JWT, продолжаем обычный путь аутентификации
        pass
        
    try:
        # Декодируем токен пользователя
        logger.info(f"Попытка декодирования токена пользователя: {actual_token[:20]}...")
        payload = jwt.decode(actual_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Используем ключ "sub" вместо "user_id" как в других сервисах
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("Токен не содержит поле 'sub'")
            return None
            
        # Возвращаем данные пользователя с добавлением токена для передачи в другие сервисы
        logger.info(f"Пользователь {user_id} успешно аутентифицирован (admin={payload.get('is_admin', False)})")
        return {
            "user_id": int(user_id),
            "is_admin": payload.get("is_admin", False),
            "is_super_admin": payload.get("is_super_admin", False),
            "token": actual_token
        }
    except PyJWTError as e:
        logger.error(f"Ошибка при декодировании токена: {str(e)}")
        return None

# Функция для проверки прав администратора
async def get_admin_user(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        current_user: Данные текущего пользователя
        
    Returns:
        Данные пользователя, если он администратор
        
    Raises:
        HTTPException: Если пользователь не является администратором или не аутентифицирован
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлены учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции",
        )
        
    return current_user

# Функция для получения параметров фильтрации заказов
def get_order_filter_params(
    page: int = 1,
    size: int = 10,
    status_id: Optional[int] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    order_by: str = "created_at",
    order_dir: str = "desc"
) -> OrderFilterParams:
    """
    Получает параметры фильтрации заказов из запроса.
    
    Args:
        page: Номер страницы
        size: Размер страницы
        status_id: ID статуса заказа
        user_id: ID пользователя
        username: Имя пользователя для поиска
        id: ID заказа
        date_from: Дата начала периода (YYYY-MM-DD)
        date_to: Дата окончания периода (YYYY-MM-DD)
        order_by: Поле для сортировки
        order_dir: Направление сортировки
        
    Returns:
        Параметры фильтрации заказов
    """
    return OrderFilterParams(
        page=page,
        size=size,
        status_id=status_id,
        user_id=user_id,
        username=username,
        id=id,
        date_from=date_from,
        date_to=date_to,
        order_by=order_by,
        order_dir=order_dir
    )

# Функция для проверки наличия товаров в сервисе продуктов
async def check_products_availability(product_ids: list[int], token: Optional[str] = None, user_id: Optional[str] = None) -> Dict[int, bool]:
    """
    Проверяет наличие товаров в сервисе продуктов.
    
    Args:
        product_ids: Список ID товаров
        token: Токен авторизации
        user_id: ID пользователя для проверки настроек уведомлений (для обратной совместимости)
        
    Returns:
        Словарь с ID товаров и их доступностью
    """
    try:
        # Получаем экземпляр API для работы с продуктами
        product_api = await get_product_api()
        
        # Получаем информацию о продуктах с использованием batch-запроса
        products = await product_api.get_products_batch(product_ids, token)
        
        # Собираем товары с низким остатком
        low_stock_products = []
        for product_id in product_ids:
            if product_id in products:
                product = products[product_id]
                if product.stock < 10:
                    # Добавляем товар в список для уведомления
                    low_stock_products.append({
                        "id": product.id,
                        "name": product.name,
                        "stock": product.stock
                    })
        
        # Отправляем уведомление только если список товаров с низким остатком не пустой 
        # и в нем есть хотя бы один товар
        if low_stock_products and len(low_stock_products) > 0:
            # Логируем информацию о товарах с низким остатком
            low_stock_names = [f"{p['name']} (ID: {p['id']}, остаток: {p['stock']})" for p in low_stock_products]
            logger.warning(f"Обнаружены товары с низким остатком: {', '.join(low_stock_names)}")
            
            # Используем глобальный флаг для отслеживания отправки уведомлений
            # Предотвращаем повторную отправку в рамках одного запроса
            if not getattr(check_products_availability, "_notification_sent", False):
                # Импортируем функцию для отправки уведомлений
                from app.services.order_service import notification_message_about_low_stock
                # Отправляем уведомление администраторам
                await notification_message_about_low_stock(low_stock_products, user_id, token)
                # Устанавливаем флаг, что уведомление уже отправлено
                check_products_availability._notification_sent = True
                logger.info(f"Запущена отправка уведомлений о {len(low_stock_products)} товарах с низким остатком")
            else:
                logger.info(f"Пропуск повторной отправки уведомления о товарах с низким остатком")
        
        logger.info(f"Products: {products}")
        
        # Проверяем наличие (stock > 0)
        result = {}
        for product_id in product_ids:
            if product_id in products:
                result[product_id] = products[product_id].stock > 0
            else:
                # Если продукт не найден, считаем его недоступным
                result[product_id] = False
        
        logger.info(f"Проверка наличия товаров: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при проверке наличия товаров: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис продуктов недоступен",
        )

# Установка начального значения для флага отправки уведомлений
check_products_availability._notification_sent = False

# Функция для получения информации о товарах из сервиса продуктов
async def get_products_info(product_ids: list[int], token: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
    """
    Получает информацию о товарах из сервиса продуктов.
    
    Args:
        product_ids: Список ID товаров
        token: Токен авторизации
        
    Returns:
        Словарь с ID товаров и информацией о них
    """
    try:
        # Получаем экземпляр API для работы с продуктами
        product_api = await get_product_api()
        
        # Получаем информацию о продуктах с использованием batch-запроса
        products = await product_api.get_products_batch(product_ids, token)
        
        # Преобразуем словарь с объектами ProductInfoSchema в словарь с dict
        result = {}
        for product_id, product in products.items():
            result[product_id] = product.to_dict()
        
        logger.info(f"Получена информация о товарах: {list(result.keys())}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении информации о товарах: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис продуктов недоступен",
        )

# Функция для получения корзины пользователя из сервиса корзин
async def get_user_cart(user_id: int) -> Dict[str, Any]:
    """
    Получает корзину пользователя из сервиса корзин.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Данные корзины пользователя
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CART_SERVICE_URL}/cart/user/{user_id}",
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"items": []}
            else:
                logger.error(f"Ошибка при получении корзины пользователя: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Сервис корзин недоступен",
                )
    except httpx.RequestError as e:
        logger.error(f"Ошибка при запросе к сервису корзин: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис корзин недоступен",
        )

# Функция для очистки корзины пользователя в сервисе корзин
async def clear_user_cart(user_id: int) -> bool:
    """
    Очищает корзину пользователя в сервисе корзин.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        True, если корзина успешно очищена
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{CART_SERVICE_URL}/cart/user/{user_id}",
                timeout=5.0
            )
            
            if response.status_code in (200, 204):
                return True
            else:
                logger.error(f"Ошибка при очистке корзины пользователя: {response.text}")
                return False
    except httpx.RequestError as e:
        logger.error(f"Ошибка при запросе к сервису корзин: {str(e)}")
        return False 