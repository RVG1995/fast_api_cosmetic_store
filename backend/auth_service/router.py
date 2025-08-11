"""Модуль аутентификации и авторизации пользователей."""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated, List, Dict, Any

# Импорты из fastapi
from fastapi import APIRouter, Depends, Cookie, HTTPException, status, Response, Request, Header, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
import secrets as _secrets

from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from models import UserModel
import jwt
from schema import TokenSchema, TokenTypeOnlySchema, UserCreateShema, UserReadSchema, PasswordChangeSchema, UserSessionsResponseSchema, PasswordResetRequestSchema, PasswordResetSchema, UserUpdateSchema
from dotenv import load_dotenv
from utils import get_password_hash, verify_password  # Импортируем из utils
from auth_utils import get_current_user, get_admin_user, get_super_admin_user  # Импортируем из auth_utils.py

# Импорты из пакета app
from app.services.email_service import send_password_reset_email
from app.services import (
    TokenService,
    bruteforce_protection,
    user_service,
    session_service,
    cache_service,
)
from app.services.auth.keys_service import get_jwks, rotate_keys

from aiosmtplib.errors import SMTPException
from aio_pika.exceptions import AMQPError
import httpx

# Настройка логгера
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

SessionDep = Annotated[AsyncSession, Depends(get_session)]

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Client Credentials: используем единый ENV SERVICE_CLIENTS_RAW
SERVICE_CLIENTS_RAW = os.getenv("SERVICE_CLIENTS_RAW", "")
SERVICE_CLIENTS = {kv.split(":")[0]: kv.split(":")[1] for kv in SERVICE_CLIENTS_RAW.split(",") if ":" in kv}
SERVICE_TOKEN_EXPIRE_MINUTES = int(os.getenv("SERVICE_TOKEN_EXPIRE_MINUTES", "15"))

router = APIRouter(prefix='/auth', tags=['Авторизация'])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# ------------------ CSRF ------------------

def _issue_csrf_token() -> str:
    return _secrets.token_urlsafe(32)

def _get_csrf_from_headers(request: Request) -> str | None:
    return request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")

def _get_csrf_from_cookies(request: Request) -> str | None:
    return request.cookies.get("csrf_token")

def _validate_csrf(request: Request) -> None:
    # Проверяем только для небезопасных методов
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        header_token = _get_csrf_from_headers(request)
        cookie_token = _get_csrf_from_cookies(request)
        if not header_token or not cookie_token or header_token != cookie_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid or missing")


@router.post("/refresh", summary="Обновление access-токена по refresh")
async def refresh_access_token(
    response: Response,
    session: SessionDep,
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
    authorization: str = Depends(oauth2_scheme)
) -> Dict[str, str]:
    """
    Обновляет access-токен по валидному refresh-токену с ротацией jti
    """
    actual_refresh = None
    if refresh_token:
        actual_refresh = refresh_token
    elif authorization:
        # допускаем Bearer refresh для внутренней отладки
        actual_refresh = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    if not actual_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = await TokenService.decode_token(actual_refresh)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")

        # Проверяем, не отозван ли refresh по jti
        refresh_jti = payload.get("jti")
        if not refresh_jti:
            raise HTTPException(status_code=400, detail="Refresh token corrupted")

        revoked = await cache_service.get(f"revoked:jti:{refresh_jti}")
        if revoked:
            raise HTTPException(status_code=401, detail="Refresh token revoked")

        # Ротация: помечаем старый refresh как отозванный
        exp_ts = payload.get("exp")
        if exp_ts:
            ttl = max(int(exp_ts - datetime.now(timezone.utc).timestamp()), 1)
            await cache_service.set(f"revoked:jti:{refresh_jti}", True, ttl)

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Refresh token missing subject")

        # Получаем пользователя, чтобы включить актуальные роли/флаги
        user = await user_service.get_user_by_id(session, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Генерим новый access и refresh с полными клеймами
        access_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "sub": str(user.id),
            "is_admin": user.is_admin,
            "is_super_admin": user.is_super_admin,
            "is_active": user.is_active,
            "email": user.email,
        }
        access_token, access_jti = await TokenService.create_access_token(data=token_data, expires_delta=access_expires)
        new_refresh, new_refresh_jti = await TokenService.create_refresh_token(user_id=str(user_id))

        # Создаем новую запись о сессии (по желанию — можно связать через кэш)
        await session_service.create_session(
            session=session,
            user_id=int(user_id),
            jti=access_jti,
            user_agent="refresh",
            ip_address="refresh",
            expires_at=datetime.now(timezone.utc) + access_expires
        )

        # Устанавливаем новые куки
        secure = os.getenv("ENVIRONMENT", "development") != "development"
        cookie_samesite = os.getenv("COOKIE_SAMESITE", "Lax")
        cookie_domain = os.getenv("COOKIE_DOMAIN", None)
        cookie_path = os.getenv("COOKIE_PATH", "/")

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite=cookie_samesite,
            secure=secure,
            domain=cookie_domain,
            path=cookie_path,
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            httponly=True,
            max_age=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", "20160")) * 60,
            samesite=cookie_samesite,
            secure=secure,
            domain=cookie_domain,
            path=cookie_path,
        )

        return {"token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/register", response_model=UserReadSchema, status_code=status.HTTP_201_CREATED, summary="Регистрация")
async def register(
    user: UserCreateShema,
    session: SessionDep,
    request: Request
) -> UserReadSchema:
    """
    Регистрация нового пользователя
    
    Args:
        user: Данные нового пользователя
        session: Сессия базы данных
        request: Объект запроса
        
    Returns:
        UserReadSchema: Данные созданного пользователя
        
    Raises:
        HTTPException: При ошибке регистрации
    """
    # Проверяем, не зарегистрирован ли уже email
    existing_user = await user_service.get_user_by_email(session, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    try:
        # Создаем пользователя
        new_user, activation_token = await user_service.create_user(
            session,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            password=user.password,
            is_active=False,
            personal_data_agreement=bool(user.personal_data_agreement),
            notification_agreement=bool(user.notification_agreement)
        )
        
        # Отправляем письмо активации
        try:
            await user_service.send_activation_email(
                str(new_user.id),
                user.email,
                activation_token
            )
        except (SMTPException, AMQPError) as email_error:
            # Логируем только SMTP-ошибки и не прерываем регистрацию
            logger.error("Ошибка при отправке письма активации: %s", email_error)
        
        # Если пользователь согласился на уведомления, активируем их        
        logger.info("Пользователь зарегистрирован: %s, ID: %s", user.email, new_user.id)
        
        return UserReadSchema(
            id=new_user.id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
        )
        
    except Exception as e:
        # Если произошла ошибка, откатываем изменения
        await session.rollback()
        logger.error("Ошибка при регистрации: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        ) from e

@router.post("/login", response_model=TokenTypeOnlySchema, summary="Вход")
async def login(
    session: SessionDep,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    response: Response = None
) -> TokenTypeOnlySchema:
    """
    Авторизация пользователя и получение JWT токена
    
    Args:
        session: Сессия базы данных
        request: Объект запроса
        form_data: Данные формы авторизации
        response: Объект ответа
        
    Returns:
        TokenSchema: JWT токен
        
    Raises:
        HTTPException: При ошибке авторизации
    """
    # Получаем IP пользователя для проверки брутфорса
    client_ip = request.client.host if hasattr(request, 'client') and request.client else "unknown"
    
    # Проверяем, не заблокирован ли IP
    is_blocked = await bruteforce_protection.check_ip_blocked(client_ip)
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много неудачных попыток входа. Пожалуйста, повторите позже."
        )
    
    # Проверяем учетные данные пользователя
    user = await user_service.verify_credentials(session, form_data.username, form_data.password)
    
    if not user:
        # Записываем неудачную попытку входа
        attempt_info = await bruteforce_protection.record_failed_attempt(
            client_ip, 
            form_data.username
        )
        
        # Если достигнут лимит попыток, блокируем IP
        if attempt_info.get("blocked", False):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много неудачных попыток входа. Повторите через {attempt_info.get('blocked_for', 300)} секунд."
            )
            
        # Стандартное сообщение об ошибке
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Получаем информацию о пользовательской сессии
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Сбрасываем счетчик неудачных попыток
    await bruteforce_protection.reset_attempts(client_ip, form_data.username)
    
    # Создаем данные для токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user.id),
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active,
        "email": user.email  # Добавляем email для удобства
    }
    
    # Создаем токен с использованием сервиса
    access_token, jti = await TokenService.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    # Вычисляем время истечения токена
    expires_at = datetime.now(timezone.utc) + access_token_expires
    
    # Создаем запись о сессии
    await session_service.create_session(
        session=session,
        user_id=user.id,
        jti=jti,
        user_agent=user_agent,
        ip_address=client_ip,
        expires_at=expires_at
    )
    
    # Обновляем дату последнего входа
    await user_service.update_last_login(session, user.id)
    
    # Создаем refresh-токен и сохраняем jti в кэше для связи/ротации
    refresh_token, refresh_jti = await TokenService.create_refresh_token(user_id=str(user.id))
    try:
        # Привязываем refresh jti к текущей сессии jti (для ротации/инвалидации)
        await cache_service.set(f"refresh:bind:{refresh_jti}", jti, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    except Exception:
        pass

    # Устанавливаем cookie с улучшенными настройками безопасности
    secure = os.getenv("ENVIRONMENT", "development") != "development"  # Secure только в production
    cookie_samesite = os.getenv("COOKIE_SAMESITE", "Lax")
    cookie_domain = os.getenv("COOKIE_DOMAIN", None)
    cookie_path = os.getenv("COOKIE_PATH", "/")

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=cookie_samesite,
        secure=secure,
        domain=cookie_domain,
        path=cookie_path,
    )

    # Кука для refresh-токена
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", "20160")) * 60,
        samesite=cookie_samesite,
        secure=secure,
        domain=cookie_domain,
        path=cookie_path,
    )

    # Выдаём/обновляем CSRF-токен (доступен JS)
    csrf_token = _issue_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        max_age=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", "20160")) * 60,
        samesite=cookie_samesite,
        secure=secure,
        domain=cookie_domain,
        path=cookie_path,
    )

    # Токен в теле ответа больше не возвращаем
    return {"token_type": "bearer"}


@router.post("/logout", summary="Выход из системы")
async def logout(
    response: Response,
    session: SessionDep,
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme),
    refresh_cookie: str = Cookie(None, alias="refresh_token")
) -> Dict[str, str]:
    """
    Выход из системы и отзыв текущего токена
    
    Args:
        response: Объект ответа
        session: Сессия базы данных
        token: Токен из cookies
        authorization: Токен из заголовка Authorization
        
    Returns:
        Dict[str, str]: Статус операции
    """
    # Пробуем получить токен сначала из куки, потом из заголовка
    actual_token = None
    if token:
        actual_token = token
    elif authorization:
        actual_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    if actual_token:
        try:
            # Декодируем токен для получения jti
            payload = await TokenService.decode_token(actual_token)
            jti = payload.get("jti")
            
            # Если в токене есть jti, отзываем сессию
            if jti:
                success = await session_service.revoke_session_by_jti(session, jti, "User logout")
                if success:
                    logger.info("Сессия с JTI %s отозвана при выходе", jti)
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError) as e:
            logger.error("Ошибка при отзыве сессии: %s", e)
    
    # Пытаемся отозвать refresh-токен, если он есть в куке
    if refresh_cookie:
        try:
            refresh_payload = await TokenService.decode_token(refresh_cookie)
            if refresh_payload.get("type") == "refresh":
                refresh_jti = refresh_payload.get("jti")
                exp_ts = refresh_payload.get("exp")
                if refresh_jti and exp_ts:
                    ttl = max(int(exp_ts - datetime.now(timezone.utc).timestamp()), 1)
                    await cache_service.set(f"revoked:jti:{refresh_jti}", True, ttl)
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError) as e:
            logger.error("Ошибка при отзыве refresh токена: %s", e)

    # Удаляем куки в любом случае
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="refresh_token")
    return {"status": "success", "message": "Успешный выход из системы"}

@router.get("/users/me/sessions", response_model=UserSessionsResponseSchema, summary="Получение списка активных сессий пользователя")
async def get_user_sessions(
    session: SessionDep, 
    current_user: UserModel = Depends(get_current_user)
) -> UserSessionsResponseSchema:
    """
    Возвращает список активных сессий пользователя.
    
    Args:
        session: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        UserSessionsResponseSchema: Список сессий пользователя
    """
    try:
        # Получаем сессии пользователя с использованием сервиса
        user_sessions = await session_service.get_user_sessions(session, current_user.id)
        
        session_data = []
        for user_session in user_sessions:
            session_data.append({
                "id": user_session.id,
                "jti": user_session.jti,
                "user_agent": user_session.user_agent,
                "ip_address": user_session.ip_address,
                "created_at": user_session.created_at,
                "expires_at": user_session.expires_at,
                "is_active": user_session.is_active
            })
        
        return {"sessions": session_data}
    except Exception as e:
        logger.error("Ошибка при получении сессий: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении информации о сессиях"
        ) from e

@router.post("/users/me/sessions/{session_id}/revoke", summary="Отзыв сессии пользователя")
async def revoke_user_session(
    session_id: int,
    session: SessionDep, 
    current_user: UserModel = Depends(get_current_user),
    request: Request = None
) -> Dict[str, str]:
    """
    Отзывает указанную сессию пользователя.
    
    Args:
        session_id: ID сессии для отзыва
        session: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Dict[str, str]: Статус операции
    """
    try:
        # Отзываем сессию с использованием сервиса
        success = await session_service.revoke_session(
            session=session,
            session_id=session_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия не найдена или не принадлежит пользователю"
            )
        
        return {"status": "success", "message": "Сессия успешно отозвана"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при отзыве сессии: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при отзыве сессии"
        ) from e

@router.post("/users/me/sessions/revoke-all", summary="Отзыв всех сессий пользователя, кроме текущей")
async def revoke_all_user_sessions(
    session: SessionDep, 
    current_user: UserModel = Depends(get_current_user),
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme),
    request: Request = None
) -> Dict[str, Any]:
    """
    Отзывает все активные сессии пользователя, кроме текущей.
    
    Args:
        session: Сессия базы данных
        current_user: Текущий пользователь
        token: Токен из cookies
        authorization: Токен из заголовка Authorization
        
    Returns:
        Dict[str, Any]: Статус операции и количество отозванных сессий
    """
    try:
        # Получаем текущий JTI из токена
        current_jti = None
        actual_token = None
        
        if token:
            actual_token = token
        elif authorization:
            actual_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        
        if actual_token:
            payload = await TokenService.decode_token(actual_token)
            current_jti = payload.get("jti")
        
        # Отзываем все сессии, кроме текущей
        revoked_count = await session_service.revoke_all_user_sessions(
            session=session,
            user_id=current_user.id,
            exclude_jti=current_jti
        )
        
        return {
            "status": "success", 
            "message": f"Отозвано {revoked_count} сессий", 
            "revoked_count": revoked_count
        }
    except Exception as e:
        logger.error("Ошибка при отзыве всех сессий: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при отзыве сессий"
        ) from e

@router.get("/users/me", response_model=None, summary="Получение базовой информации о текущем пользователе")
async def read_users_me_basic(current_user: UserModel = Depends(get_current_user)):
    """
    Базовый эндпоинт для проверки аутентификации пользователя.
    Возвращает только идентификатор и статус пользователя.
    """
    # Базовые данные для всех пользователей
    base_data = {
        "id": current_user.id,

    }
    

    
    return base_data

@router.get("/users/me/profile", response_model=None, summary="Получение полного профиля текущего пользователя")
async def read_users_me_profile(current_user: UserModel = Depends(get_current_user)):
    """
    Полный профиль пользователя со всеми данными.
    Используется для отображения и редактирования профиля.
    """
    # Базовые данные для всех пользователей
    base_data = {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email
    }
    
    # Если пользователь админ или суперадмин, возвращаем расширенные данные
    if current_user.is_admin or current_user.is_super_admin:
        from schema import AdminUserReadShema
        return AdminUserReadShema(
            **base_data,
            is_active=current_user.is_active,
            is_admin=current_user.is_admin,
            is_super_admin=current_user.is_super_admin
        )
    else:
        from schema import UserReadSchema
        return UserReadSchema(**base_data)

@router.get("/activate/{token}", summary="Активация аккаунта")
async def activate_user(
    token: str,
    session: SessionDep,
    response: Response
) -> Dict[str, Any]:
    """
    Активирует аккаунт пользователя по токену из письма
    
    Args:
        token: Токен активации
        session: Сессия базы данных
        response: Объект ответа
        
    Returns:
        Dict[str, Any]: Статус операции и данные пользователя
    """
    # Активируем пользователя с использованием сервиса
    user = await user_service.activate_user(session, token)
    
    if not user:
        raise HTTPException(status_code=400, detail="Недействительный токен активации")
    
    # Создаем токен доступа
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user.id),
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active,
        "email": user.email
    }
    
    # Создаем JWT токен
    access_token, jti = await TokenService.create_access_token(
        data=token_data, 
        expires_delta=access_token_expires
    )
    
    # Устанавливаем cookie
    secure = os.getenv("ENVIRONMENT", "development") != "development"
    cookie_samesite = os.getenv("COOKIE_SAMESITE", "Lax")
    cookie_domain = os.getenv("COOKIE_DOMAIN", None)
    cookie_path = os.getenv("COOKIE_PATH", "/")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=cookie_samesite,
        secure=secure,
        domain=cookie_domain,
        path=cookie_path,
    )
    
    logger.info("Аккаунт активирован: %s, ID: %s", user.email, user.id)

    # Если пользователь согласился на уведомления, активируем их
    if bool(user.notification_agreement):
        logger.info("Активация уведомлений для пользователя: %s, ID: %s", user.email, user.id)
        try:
            # Создаем сервисный токен напрямую через TokenService
            service_token, _ = await TokenService.create_access_token(
                data={
                    "sub": "auth_service", 
                    "scope": "service"
                },
                expires_delta=timedelta(minutes=SERVICE_TOKEN_EXPIRE_MINUTES)
            )
            
            if not service_token:
                logger.error("Не удалось создать сервисный токен")
                raise ValueError("Failed to create service token")
            
            # Активируем уведомления с полученным токеном
            notifications_result = await user_service.activate_notifications(
                str(user.id),
                user.email,
                is_admin=user.is_admin,
                service_token=service_token
            )
            
            if notifications_result:
                logger.info("Уведомления успешно активированы для пользователя: %s", user.email)
            else:
                logger.warning("Не удалось активировать уведомления для пользователя: %s", user.email)
                
        except httpx.RequestError as notification_error:
            logger.error("Ошибка при активации уведомлений: %s", notification_error)
    
    return {
        "status": "success",
        "message": "Аккаунт успешно активирован",
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email
        }
    }

@router.post("/change-password", status_code=status.HTTP_200_OK, summary="Смена пароля")
async def change_password(
    password_data: PasswordChangeSchema,
    session: SessionDep,
    current_user: UserModel = Depends(get_current_user),
    request: Request = None
) -> Dict[str, str]:
    """
    Смена пароля пользователя.
    
    Args:
        password_data: Данные для смены пароля
        session: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Dict[str, str]: Статус операции
    """
    # CSRF
    _validate_csrf(request)

    # Проверяем текущий пароль
    if not await verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Изменяем пароль с использованием сервиса
    success = await user_service.change_password(
        session=session,
        user_id=current_user.id,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось изменить пароль"
        )
    
    logger.info("Пароль изменен для пользователя: %s, ID: %s", current_user.email, current_user.id)
    
    return {"status": "success", "message": "Пароль успешно изменен"}

@router.get("/users/me/permissions", summary="Проверка разрешений пользователя")
async def check_user_permissions(
    permission: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Проверяет разрешения пользователя для определенных ресурсов и действий.
    
    Args:
        permission: Тип разрешения (например, "read", "write", "delete")
        resource_type: Тип ресурса (например, "order", "product", "user")
        resource_id: ID конкретного ресурса (если применимо)
        current_user: Текущий пользователь
    
    Returns:
        Dict с результатами проверки разрешения
    """
    logger.info("Запрос проверки разрешений для пользователя ID=%s, permission=%s", current_user.id, permission)

    result = {
        "is_authenticated": True,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "is_super_admin": current_user.is_super_admin,
    }

    if permission:
        if current_user.is_super_admin:
            result["has_permission"] = True
            return result
        if permission == "admin_access":
            if not (current_user.is_admin or current_user.is_super_admin):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
            result["has_permission"] = True
            return result
        if permission == "read":
            result["has_permission"] = True
        elif permission in ["write", "update"]:
            if resource_type == "user" and resource_id == current_user.id:
                result["has_permission"] = True
            elif current_user.is_admin:
                result["has_permission"] = True
            else:
                result["has_permission"] = False
        elif permission == "delete":
            result["has_permission"] = current_user.is_admin
        elif permission == "super_admin_access":
            result["has_permission"] = current_user.is_super_admin
        else:
            result["has_permission"] = False
    return result

@router.post("/request-password-reset")
async def request_password_reset(data: PasswordResetRequestSchema, session: SessionDep, request: Request):
    """
    Запрашивает сброс пароля для пользователя по email.
    
    Args:
        data: Данные запроса сброса пароля
        session: Сессия базы данных
        
    Returns:
        Dict[str, str]: Статус операции
    """
    user = await user_service.get_user_by_email(session, data.email)
    if not user:
        return {"status": "ok"}
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_created_at = datetime.now(timezone.utc)
    await session.commit()
    await send_password_reset_email(str(user.id), user.email, token)
    return {"status": "ok"}

@router.post("/reset-password")
async def reset_password(data: PasswordResetSchema, session: SessionDep, request: Request):
    """
    Сбрасывает пароль пользователя по токену.
    
    Args:
        data: Данные для сброса пароля
        session: Сессия базы данных
        
    Returns:
        Dict[str, str]: Статус операции
        
    Raises:
        HTTPException: При неверном токене или несовпадении паролей
    """
    user = await UserModel.get_by_reset_token(session, data.token)
    if not user or not user.reset_token or user.reset_token != data.token:
        raise HTTPException(status_code=400, detail="Неверный или истёкший токен")
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")
    user.hashed_password = await get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_created_at = None
    await session.commit()
    return {"status": "success"}

@router.get("/.well-known/jwks.json")
async def jwks():
    return get_jwks()


@router.post("/keys/rotate", dependencies=[Depends(get_super_admin_user)], summary="Ротация RSA ключей (RS256)")
async def rotate_rsa_keys(keep_seconds: int | None = None):
    new_kid, kept_until = rotate_keys(keep_seconds)
    return {"status": "ok", "new_kid": new_kid, "old_keys_kept_until": kept_until}

# Добавляем функцию зависимости для проверки service_key или прав суперадмина
async def verify_service_key_or_super_admin(
    service_key: str = Header(None, alias="service-key"),
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> bool:
    """
    Проверяет, что запрос содержит правильный сервисный ключ или
    что пользователь имеет права суперадминистратора.
    Одно из условий должно быть выполнено.
    """
    INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "test")
    
    # Проверка сервисного ключа
    if service_key and service_key == INTERNAL_SERVICE_KEY:
        logger.info("Запрос авторизован через сервисный ключ")
        return True
    
    # Проверка прав суперадминистратора у текущего пользователя
    if current_user and current_user.is_super_admin:
        logger.info("Запрос авторизован суперадминистратором ID=%s", current_user.id)
        return True
    
    # Если ни один из методов не подошел, выбрасываем исключение
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Требуется сервисный ключ или права суперадминистратора"
    )
bearer_scheme = HTTPBearer(auto_error=False)
async def verify_service_jwt(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> bool:
    """Проверяет JWT токен с scope 'service'"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        # RS256: проверяем подпись публичным ключом
        from app.services.auth.keys_service import get_public_key_pem
        payload = jwt.decode(cred.credentials, get_public_key_pem(), algorithms=["RS256"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True
# Добавляем новый эндпоинт для получения списка администраторов
@router.get("/admins", summary="Получение списка всех администраторов и суперадминистраторов", dependencies=[Depends(verify_service_jwt)])
async def get_all_admins(
    session: SessionDep,
) -> List[Dict[str, Any]]:
    """
    Получает список всех пользователей с правами администратора и суперадминистратора.
    Возвращает только ID и информацию о правах, без персональных данных.
    
    Доступ:
    - Только с сервисным ключом (service-key)
    - Или для пользователей с правами суперадминистратора
    """
    logger.info("Запрос на получение списка администраторов")
    
    # Используем метод класса для получения всех администраторов
    admins = await UserModel.get_all_admins(session)
    
    # Формируем список только с нужными полями
    admins_list = [
        {
            "email": admin.email,
        }
        for admin in admins
    ]
    
    logger.info("Найдено %d администраторов", len(admins_list))
    return admins_list


@router.get("/all/users", summary="Получение списка всех пользователей", dependencies=[Depends(get_admin_user)])
async def get_all_users(
    session: SessionDep,
) -> List[Dict[str, Any]]:
    """
    Получает список всех пользователей.
    Доступ:
    - Только для администраторов
    """
    logger.info("Запрос на получение списка всех пользователей")
    
    # Используем метод класса для получения всех пользователей
    users = await UserModel.get_all_users(session)
    
    # Преобразуем объекты UserModel в словари
    users_list = [
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "is_super_admin": user.is_super_admin
        }
        for user in users
    ]
    
    logger.info("Найдено %d пользователей", len(users_list))
    return users_list


@router.post("/token", response_model=TokenSchema, summary="Client Credentials Token")
async def service_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    """
    Получение JWT токена для сервисного доступа.
    
    Args:
        grant_type: Тип гранта (должен быть "client_credentials")
        client_id: Идентификатор клиента
        client_secret: Секретный ключ клиента
        
    Returns:
        TokenSchema: JWT токен доступа
        
    Raises:
        HTTPException: При неверных учетных данных или неподдерживаемом типе гранта
    """
    logger.info("Token request received: grant_type=%s, client_id=%s", grant_type, client_id)
    if grant_type != "client_credentials":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported grant_type")
    # Получаем секрет из mapping и проверяем
    secret = SERVICE_CLIENTS.get(client_id)
    if not secret or secret != client_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client credentials")
    expires = timedelta(minutes=SERVICE_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": client_id, "scope": "service"}
    access_token, jti = await TokenService.create_access_token(token_data, expires_delta=expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.patch("/users/{user_id}/toggle-active", summary="Изменение статуса активности пользователя", dependencies=[Depends(get_super_admin_user)])
async def toggle_user_active_status(
    user_id: int,
    session: SessionDep,
    current_user: UserModel = Depends(get_super_admin_user)
) -> Dict[str, Any]:
    """
    Изменяет статус активности пользователя (активный/неактивный).
    Только суперадминистраторы могут изменять статус пользователей.
    
    Args:
        user_id: ID пользователя для изменения статуса
        session: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Dict[str, Any]: Статус операции и обновленный статус пользователя
        
    Raises:
        HTTPException: Если пользователь не найден или текущий пользователь не имеет прав суперадминистратора
    """
    # Проверяем, что текущий пользователь - суперадминистратор
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только суперадминистраторы могут изменять статус активности пользователей"
        )
    
    # Получаем пользователя, которого нужно изменить
    user = await UserModel.get_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Меняем статус активности на противоположный
    user.is_active = not user.is_active
    await session.commit()
    
    logger.info(
        "Статус активности пользователя %s (ID: %s) изменен суперадминистратором %s (ID: %s). Новый статус: %s",
        user.email, user.id, current_user.email, current_user.id, user.is_active
    )
    
    return {
        "status": "success",
        "message": f"Статус активности пользователя {user.email} изменен",
        "is_active": user.is_active
    }

@router.post("/users", response_model=UserReadSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_super_admin_user)], summary="Создание пользователя суперадминистратором")
async def create_user_by_admin(
    user: UserCreateShema,
    session: SessionDep,
    is_admin: bool = False,
    current_user: UserModel = Depends(get_super_admin_user)
) -> UserReadSchema:
    """
    Создание нового пользователя суперадминистратором без отправки подтверждения.
    Пользователь будет автоматически активирован.
    
    Args:
        user: Данные нового пользователя
        session: Сессия базы данных
        is_admin: Флаг, определяющий, будет ли пользователь администратором
        current_user: Текущий суперадминистратор
        
    Returns:
        UserReadSchema: Данные созданного пользователя
        
    Raises:
        HTTPException: При ошибке создания пользователя
    """
    # Проверяем, не зарегистрирован ли уже email
    existing_user = await user_service.get_user_by_email(session, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    try:
        # Создаем пользователя, сразу активированного
        new_user, _ = await user_service.create_user(
            session,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            password=user.password,
            is_active=True,  # Автоматически активируем пользователя
            is_admin=is_admin,  # Устанавливаем права администратора если указано
            personal_data_agreement=bool(user.personal_data_agreement),
            notification_agreement=bool(user.notification_agreement)
        )
        
        logger.info(
            "Пользователь %s (ID: %s) создан суперадминистратором %s (ID: %s), is_admin=%s",
            new_user.email, new_user.id, current_user.email, current_user.id, is_admin
        )
        
        return UserReadSchema(
            id=new_user.id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
        )
        
    except Exception as e:
        # Если произошла ошибка, откатываем изменения
        await session.rollback()
        logger.error("Ошибка при создании пользователя суперадминистратором: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Произошла ошибка при создании пользователя. Пожалуйста, попробуйте позже."
        ) from e

@router.patch("/users/me/profile", response_model=UserReadSchema, summary="Обновление профиля пользователя",dependencies=[Depends(get_current_user)])
async def update_user_profile(
    update_data: UserUpdateSchema,
    session: SessionDep,
    current_user: UserModel = Depends(get_current_user)
) -> UserReadSchema:
    """
    Обновление профиля текущего пользователя (имя, фамилия, email).
    
    Args:
        update_data: Данные для обновления
        session: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        UserReadSchema: Обновленные данные пользователя
        
    Raises:
        HTTPException: При ошибке обновления профиля
    """
    try:
        # Проверяем, меняется ли email
        if update_data.email and update_data.email != current_user.email:
            # Проверяем уникальность email
            existing_user = await user_service.get_user_by_email(session, update_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email уже зарегистрирован другим пользователем"
                )
        
        # Обновляем данные пользователя
        if update_data.first_name:
            current_user.first_name = update_data.first_name
        
        if update_data.last_name:
            current_user.last_name = update_data.last_name
        
        if update_data.email:
            current_user.email = update_data.email
        
        # Сохраняем изменения
        await session.commit()
        
        # Инвалидируем кэш для данного пользователя через user_service
        # Внутренние методы сервиса уже имеют логику для инвалидации кэша
        # Получаем пользователя заново, чтобы обновить кэш
        await user_service.get_user_by_id(session, current_user.id)
        await user_service.get_user_by_email(session, current_user.email)
        
        logger.info("Профиль пользователя обновлен: ID=%s, email=%s", current_user.id, current_user.email)
        
        return UserReadSchema(
            id=current_user.id,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email
        )
        
    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
    except Exception as e:
        # Логируем ошибку и возвращаем 500
        logger.error("Ошибка при обновлении профиля: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении профиля"
        ) from e
