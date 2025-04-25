from fastapi import APIRouter, Depends, Cookie, HTTPException, status, Response, BackgroundTasks, Request, Header, Form
from sqlalchemy import select 
from typing import Optional, Annotated, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from models import UserModel, UserSessionModel
import jwt
from schema import TokenSchema, UserCreateShema, UserReadSchema, PasswordChangeSchema, UserSessionsResponseSchema, PasswordResetRequestSchema, PasswordResetSchema
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os
from dotenv import load_dotenv
from utils import get_password_hash, verify_password  # Импортируем из utils
from app.services.email_service import send_email_activation_message, send_password_reset_email
import logging
import uuid  # Если это еще не импортировано
from auth_utils import get_current_user, get_admin_user  # Импортируем из auth_utils.py

# Импортируем наши сервисы
from app.services import (
    TokenService,
    bruteforce_protection,
    user_service,
    session_service,
    cache_service
)

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
logger.info(f"SERVICE_CLIENTS keys: {list(SERVICE_CLIENTS.keys())}")

router = APIRouter(prefix='/auth', tags=['Авторизация'])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD'),
    MAIL_FROM = os.getenv('MAIL_FROM'),
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465)),
    MAIL_SERVER = os.getenv('MAIL_SERVER'),
    MAIL_STARTTLS = os.getenv('MAIL_STARTTLS', 'False').lower() == 'true',
    MAIL_SSL_TLS = os.getenv('MAIL_SSL_TLS', 'True').lower() == 'true'
)

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
            is_active=False
        )
        
        # Отправляем письмо активации
        await user_service.send_activation_email(
            str(new_user.id),
            user.email,
            activation_token
        )
        
        logger.info(f"Пользователь зарегистрирован: {user.email}, ID: {new_user.id}")
        
        return UserReadSchema(
            id=new_user.id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
        )
        
    except Exception as e:
        # Если произошла ошибка, откатываем изменения
        await session.rollback()
        logger.error(f"Ошибка при регистрации: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        )

@router.post("/login", response_model=TokenSchema, summary="Вход")
async def login(
    session: SessionDep, 
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    response: Response = None
) -> TokenSchema:
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
    
    # Устанавливаем cookie с улучшенными настройками безопасности
    secure = os.getenv("ENVIRONMENT", "development") != "development"  # Secure только в production
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="Lax",  # Меняем на Lax для кросс-доменных запросов
        secure=secure,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", summary="Выход из системы")
async def logout(
    response: Response, 
    session: SessionDep,
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
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
                    logger.info(f"Сессия с JTI {jti} отозвана при выходе")
        except Exception as e:
            logger.error(f"Ошибка при отзыве сессии: {str(e)}")
    
    # Удаляем куки в любом случае
    response.delete_cookie(key="access_token")
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
                "expires_at": user_session.expires_at
            })
        
        return {"sessions": session_data}
    except Exception as e:
        logger.error(f"Ошибка при получении сессий: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении информации о сессиях"
        )

@router.post("/users/me/sessions/{session_id}/revoke", summary="Отзыв сессии пользователя")
async def revoke_user_session(
    session_id: int,
    session: SessionDep, 
    current_user: UserModel = Depends(get_current_user)
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
        logger.error(f"Ошибка при отзыве сессии: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при отзыве сессии"
        )

@router.post("/users/me/sessions/revoke-all", summary="Отзыв всех сессий пользователя, кроме текущей")
async def revoke_all_user_sessions(
    session: SessionDep, 
    current_user: UserModel = Depends(get_current_user),
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
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
        logger.error(f"Ошибка при отзыве всех сессий: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при отзыве сессий"
        )

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
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="Lax",
        secure=secure
    )
    
    logger.info(f"Аккаунт активирован: {user.email}, ID: {user.id}")
    
    return {
        "status": "success",
        "message": "Аккаунт успешно активирован",
        "access_token": access_token,
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
    current_user: UserModel = Depends(get_current_user)
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
    
    logger.info(f"Пароль изменен для пользователя: {current_user.email}, ID: {current_user.id}")
    
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
    logger.info(f"Запрос проверки разрешений для пользователя ID={current_user.id}, permission={permission}")

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
                from fastapi import HTTPException, status
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
async def request_password_reset(data: PasswordResetRequestSchema, session: SessionDep):
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
async def reset_password(data: PasswordResetSchema, session: SessionDep):
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
        logger.info(f"Запрос авторизован суперадминистратором ID={current_user.id}")
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
        payload = jwt.decode(cred.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("scope") != "service":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return True
# Добавляем новый эндпоинт для получения списка администраторов
@router.get("/admins", summary="Получение списка всех администраторов и суперадминистраторов")
async def get_all_admins(
    session: SessionDep,
    _: bool = Depends(verify_service_jwt)
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
            "id": admin.id,
            "is_admin": admin.is_admin,
            "is_super_admin": admin.is_super_admin
        }
        for admin in admins
    ]
    
    logger.info(f"Найдено {len(admins_list)} администраторов")
    return admins_list


@router.get("/all/users", summary="Получение списка всех пользователей")
async def get_all_users(
    session: SessionDep,
    _: bool = Depends(get_admin_user)
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
        }
        for user in users
    ]
    
    logger.info(f"Найдено {len(users_list)} пользователей")
    return users_list


@router.post("/token", response_model=TokenSchema, summary="Client Credentials Token")
async def service_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    logger.info(f"Token request received: grant_type={grant_type}, client_id={client_id}")
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