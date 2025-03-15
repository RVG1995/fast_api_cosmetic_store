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

# Сервисный API-ключ для внутренней авторизации между микросервисами
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "service_secret_key_for_internal_use")

# Схема OAuth2 для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Функция для проверки токена и получения данных пользователя
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    x_service_name: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Проверяет токен и возвращает данные пользователя.
    Если токен отсутствует, возвращает None для поддержки анонимных пользователей.
    Поддерживает сервисную авторизацию для внутренних запросов между микросервисами.
    
    Args:
        token: Токен доступа из OAuth2
        authorization: Заголовок Authorization
        x_service_name: Название сервиса для внутренних запросов
        
    Returns:
        Данные пользователя или None, если токен отсутствует
    """
    # Если токен не получен через OAuth2, пробуем получить из заголовка Authorization
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    
    # Проверяем сервисный API-ключ для внутренних запросов
    if token == SERVICE_API_KEY and x_service_name:
        logger.info(f"Внутренний запрос от сервиса {x_service_name} авторизован")
        # Возвращаем специальные данные для внутреннего сервиса с повышенными правами
        return {
            "user_id": None,
            "is_admin": True,
            "is_super_admin": True,
            "is_service": True,
            "service_name": x_service_name,
            "token": token
        }
    
    # Если токен отсутствует, возвращаем None для поддержки анонимных пользователей
    if not token:
        logger.info("Токен не предоставлен")
        return None
        
    try:
        # Декодируем токен
        logger.info(f"Попытка декодирования токена: {token[:20]}...")
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
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
            "token": token
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
        id=id,
        date_from=date_from,
        date_to=date_to,
        order_by=order_by,
        order_dir=order_dir
    )

# Функция для проверки наличия товаров в сервисе продуктов
async def check_products_availability(product_ids: list[int], token: Optional[str] = None) -> Dict[int, bool]:
    """
    Проверяет наличие товаров в сервисе продуктов.
    
    Args:
        product_ids: Список ID товаров
        token: Токен авторизации
        
    Returns:
        Словарь с ID товаров и их доступностью
    """
    try:
        # Получаем экземпляр API для работы с продуктами
        product_api = await get_product_api()
        
        # Получаем информацию о продуктах с использованием batch-запроса
        products = await product_api.get_products_batch(product_ids, token)
        
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