from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import os
import jwt
from jwt.exceptions import PyJWTError
import logging
import httpx
from dotenv import load_dotenv

from database import get_db
from schemas import OrderFilterParams

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

# Схема OAuth2 для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Функция для проверки токена и получения данных пользователя
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Проверяет токен и возвращает данные пользователя.
    
    Args:
        token: Токен доступа из OAuth2
        authorization: Заголовок Authorization
        
    Returns:
        Данные пользователя
        
    Raises:
        HTTPException: Если токен недействителен или отсутствует
    """
    # Если токен не получен через OAuth2, пробуем получить из заголовка Authorization
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлены учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Декодирование токена
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверка роли пользователя
        is_admin = payload.get("is_admin", False)
        
        return {
            "user_id": int(user_id),
            "is_admin": is_admin,
            "email": payload.get("email"),
            "full_name": payload.get("full_name")
        }
    except PyJWTError as e:
        logger.error(f"Ошибка при декодировании токена: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Функция для проверки прав администратора
async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        current_user: Данные текущего пользователя
        
    Returns:
        Данные пользователя
        
    Raises:
        HTTPException: Если пользователь не является администратором
    """
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
        order_by=order_by,
        order_dir=order_dir
    )

# Функция для проверки наличия товаров в сервисе продуктов
async def check_products_availability(product_ids: list[int]) -> Dict[int, bool]:
    """
    Проверяет наличие товаров в сервисе продуктов.
    
    Args:
        product_ids: Список ID товаров
        
    Returns:
        Словарь с ID товаров и их доступностью
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PRODUCT_SERVICE_URL}/api/products/check-availability",
                json={"product_ids": product_ids},
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка при проверке наличия товаров: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Сервис продуктов недоступен",
                )
    except httpx.RequestError as e:
        logger.error(f"Ошибка при запросе к сервису продуктов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис продуктов недоступен",
        )

# Функция для получения информации о товарах из сервиса продуктов
async def get_products_info(product_ids: list[int]) -> Dict[int, Dict[str, Any]]:
    """
    Получает информацию о товарах из сервиса продуктов.
    
    Args:
        product_ids: Список ID товаров
        
    Returns:
        Словарь с ID товаров и информацией о них
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PRODUCT_SERVICE_URL}/api/products/batch",
                json={"product_ids": product_ids},
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка при получении информации о товарах: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Сервис продуктов недоступен",
                )
    except httpx.RequestError as e:
        logger.error(f"Ошибка при запросе к сервису продуктов: {str(e)}")
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
                f"{CART_SERVICE_URL}/api/cart/user/{user_id}",
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
                f"{CART_SERVICE_URL}/api/cart/user/{user_id}",
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