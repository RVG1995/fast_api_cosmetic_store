"""Зависимости и утилиты для сервиса заказов."""

import logging
from datetime import datetime, timezone

from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status, Header, Cookie
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import PyJWTError
import httpx
from cache import get_cached_data, set_cached_data

from schemas import OrderFilterParams
from product_api import get_product_api
from config import settings, get_service_clients
from auth_utils import get_service_token

# Настройка логирования
logger = logging.getLogger("order_dependencies")

# Получение настроек JWT из конфигурации
JWT_ALGORITHM = "RS256"
JWT_ISSUER = getattr(settings, "JWT_ISSUER", "auth_service")
VERIFY_JWT_AUDIENCE = getattr(settings, "VERIFY_JWT_AUDIENCE", False)
JWT_AUDIENCE = getattr(settings, "JWT_AUDIENCE", None)

# URL сервисов из конфигурации
PRODUCT_SERVICE_URL = settings.PRODUCT_SERVICE_URL
CART_SERVICE_URL = settings.CART_SERVICE_URL
AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL
NOTIFICATION_SERVICE_URL = settings.NOTIFICATION_SERVICE_URL

# Client credentials для межсервисной авторизации
SERVICE_CLIENTS = get_service_clients()
SERVICE_CLIENT_ID = settings.SERVICE_CLIENT_ID
SERVICE_TOKEN_URL = f"{AUTH_SERVICE_URL}/auth/token"
SERVICE_TOKEN_EXPIRE_MINUTES = settings.SERVICE_TOKEN_EXPIRE_MINUTES

ALGORITHM = JWT_ALGORITHM

bearer_scheme = HTTPBearer(auto_error=False)

async def _get_service_token():
    # try cache
    token = await get_cached_data("service_token")
    if token:
        return token
    # Получаем секрет из SERVICE_CLIENTS
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
    except (jwt.InvalidTokenError, jwt.DecodeError):
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
        # RS256: проверяем подпись через JWKS auth-сервиса
        jwks_client = jwt.PyJWKClient(f"{AUTH_SERVICE_URL}/auth/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(cred.credentials).key
        # Отключаем verify_aud для сервисных токенов
        payload = jwt.decode(cred.credentials, signing_key, algorithms=[ALGORITHM], options={"verify_aud": False})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
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
    logger.info("Получен токен из куки: %s", token)
    logger.info("Получен токен из заголовка: %s", authorization)

    actual_token = None
    
    # Если токен есть в куках, используем его
    if token:
        actual_token = token
        logger.info("Используем токен из куки: %s...", token[:20])
    # Если в куках нет, но есть в заголовке, используем его
    elif authorization:
        if authorization.startswith('Bearer '):
            actual_token = authorization[7:]
        else:
            actual_token = authorization
        logger.info("Используем токен из заголовка Authorization: %s...", actual_token[:20])
    
    # Если токен не найден, возвращаем None для анонимного доступа
    if actual_token is None:
        logger.info("Токен не найден, продолжаем с анонимным доступом")
        return None
    
    # Проверяем, это сервисный JWT с параметром scope=service
    try:
        decode_kwargs = {
            "algorithms": [ALGORITHM],
            "issuer": JWT_ISSUER,
            "options": {"verify_aud": VERIFY_JWT_AUDIENCE},
        }
        if VERIFY_JWT_AUDIENCE and JWT_AUDIENCE:
            decode_kwargs["audience"] = JWT_AUDIENCE
        jwks_client = jwt.PyJWKClient(f"{AUTH_SERVICE_URL}/auth/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(actual_token).key
        payload = jwt.decode(actual_token, signing_key, **decode_kwargs)
        if payload.get("scope") == "service" and x_service_name:
            logger.info("Внутренний запрос от сервиса %s авторизован через JWT", x_service_name)
            # Возвращаем специальные данные для внутреннего сервиса с повышенными правами
            return {
                "user_id": None,
                "is_admin": True,
                "is_super_admin": True,
                "is_service": True,
                "service_name": x_service_name,
                "token": actual_token
            }
    except (jwt.InvalidTokenError, jwt.DecodeError):
        # Если не сервисный JWT, продолжаем обычный путь аутентификации
        pass
        
    try:
        # Декодируем токен пользователя
        logger.info("Попытка декодирования токена пользователя: %s...", actual_token[:20])
        decode_kwargs = {
            "algorithms": [JWT_ALGORITHM],
            "issuer": JWT_ISSUER,
            "options": {"verify_aud": VERIFY_JWT_AUDIENCE},
        }
        if VERIFY_JWT_AUDIENCE and JWT_AUDIENCE:
            decode_kwargs["audience"] = JWT_AUDIENCE
        jwks_client = jwt.PyJWKClient(f"{AUTH_SERVICE_URL}/auth/.well-known/jwks.json")
        signing_key = jwks_client.get_signing_key_from_jwt(actual_token).key
        payload = jwt.decode(actual_token, signing_key, **decode_kwargs)

        # Проверяем отзыв jti (если есть)
        jti = payload.get("jti")
        if jti:
            try:
                revoked = await get_cached_data(f"revoked:jti:{jti}")
                if revoked:
                    logger.error("Токен с jti=%s отозван", jti)
                    return None
            except Exception as e:
                logger.error("Ошибка проверки revoked JTI: %s", e)
        
        # Используем ключ "sub" вместо "user_id" как в других сервисах
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("Токен не содержит поле 'sub'")
            return None
            
        # Возвращаем данные пользователя с добавлением токена для передачи в другие сервисы
        logger.info("Пользователь %s успешно аутентифицирован (admin=%s)", user_id, payload.get('is_admin', False))
        return {
            "user_id": int(user_id),
            "is_admin": payload.get("is_admin", False),
            "is_super_admin": payload.get("is_super_admin", False),
            "token": actual_token
        }
    except PyJWTError as e:
        logger.error("Ошибка при декодировании токена: %s", str(e))
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

async def notify_low_stock_products(low_stock_products: List[Dict[str, Any]]) -> bool:
    """
    Отправляет уведомление о товарах с низким остатком в сервис уведомлений
    
    Args:
        low_stock_products: Список товаров с низким остатком
            [{"id": int, "name": str, "stock": int}, ...]
        
    Returns:
        bool: True если отправка успешна, False в противном случае
    """
    try:
        logger.info("Отправка уведомления о низком остатке товаров: %d товаров", len(low_stock_products))
        
        # Получаем сервисный токен
        token = await get_service_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Отправляем запрос в сервис уведомлений
        async with httpx.AsyncClient() as client:
            # Используем эндпоинт для отправки уведомлений админам
            # Не указываем user_id, чтобы отправить всем админам
            response = await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/notifications/settings/events",
                headers=headers,
                json={
                    "event_type": "product.low_stock",
                    "user_id": None,  # Отправляем всем админам
                    "low_stock_products": low_stock_products
                },
                timeout=5.0
            )
            
            if response.status_code == 200:
                logger.info("Уведомление о низком остатке товаров успешно отправлено")
                return True
            else:
                logger.warning("Ошибка при отправке уведомления: %s, %s", response.status_code, response.text)
                return False
                
    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error("Ошибка при отправке уведомления: %s", str(e))
        return False

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
        # Получаем экземпляр API для работы с продуктами
        product_api = await get_product_api()
        
        # Получаем информацию о продуктах с использованием batch-запроса
        products = await product_api.get_products_batch(product_ids)
        
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
            logger.warning("Обнаружены товары с низким остатком: %s", ', '.join(low_stock_names))
            
            # Создаем уникальный ключ на основе ID товаров и их остатков
            # Это позволит отправлять уведомления при изменении остатка или составе товаров
            product_ids_str = "_".join([f"{p['id']}:{p['stock']}" for p in low_stock_products])
            cache_key = f"notification_sent:{product_ids_str}"
            
            # Проверяем, было ли уже отправлено уведомление для этих товаров
            already_sent = await get_cached_data(cache_key)
            
            if not already_sent:
                # Отправляем уведомление администраторам
                notification_result = await notify_low_stock_products(low_stock_products)
                
                # Если успешно, кэшируем результат на 30 минут (1800 секунд)
                # Это предотвратит отправку одинаковых уведомлений слишком часто
                if notification_result:
                    await set_cached_data(cache_key, True, 1800)
                    logger.info("Успешно отправлено уведомление о %d товарах с низким остатком", len(low_stock_products))
                else:
                    logger.warning("Не удалось отправить уведомление о товарах с низким остатком")
            else:
                logger.info("Пропуск повторной отправки уведомления о товарах с низким остатком (отправлено недавно)")
        
        logger.info("Products: %s", products)
        
        # Проверяем наличие (stock > 0)
        result = {}
        for product_id in product_ids:
            if product_id in products:
                result[product_id] = products[product_id].stock > 0
            else:
                # Если продукт не найден, считаем его недоступным
                result[product_id] = False
        
        logger.info("Проверка наличия товаров: %s", result)
        return result
    except Exception as e:
        logger.error("Ошибка при проверке наличия товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис продуктов недоступен",
        ) from e

# Функция для получения информации о товарах из сервиса продуктов
async def get_products_info(product_ids: list[int]) -> Dict[int, Dict[str, Any]]:
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
        products = await product_api.get_products_batch(product_ids)
        
        # Преобразуем словарь с объектами ProductInfoSchema в словарь с dict
        result = {}
        for product_id, product in products.items():
            result[product_id] = product.to_dict()
        
        logger.info("Получена информация о товарах: %s", list(result.keys()))
        return result
    except Exception as e:
        logger.error("Ошибка при получении информации о товарах: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис продуктов недоступен",
        ) from e

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
                logger.error("Ошибка при получении корзины пользователя: %s", response.text)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Сервис корзин недоступен",
                )
    except httpx.RequestError as e:
        logger.error("Ошибка при запросе к сервису корзин: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис корзин недоступен",
        ) from e

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
                logger.error("Ошибка при очистке корзины пользователя: %s", response.text)
                return False
    except httpx.RequestError as e:
        logger.error("Ошибка при запросе к сервису корзин: %s", str(e))
        return False
