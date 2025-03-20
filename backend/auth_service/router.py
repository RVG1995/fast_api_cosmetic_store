from fastapi import APIRouter,Depends,Cookie,HTTPException,status,Response, BackgroundTasks, Request
from sqlalchemy import select 
from typing import Optional, Annotated, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database import  get_session
from models import UserModel, UserSessionModel
import jwt
from schema import TokenShema, UserCreateShema, UserReadShema, PasswordChangeSchema
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os
from dotenv import load_dotenv
from utils import get_password_hash, verify_password  # Импортируем из utils
from app.services.email_service import send_verification_email
import logging
import uuid  # Если это еще не импортировано

# Настройка логгера
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

SessionDep = Annotated[AsyncSession,Depends(get_session)]

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

router = APIRouter(prefix='/auth', tags=['Авторизация'])

async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Добавляем уникальный идентификатор токена (jti) для возможности отзыва
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, jti  # Возвращаем и токен, и его jti

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

async def get_current_user(
    session: SessionDep, 
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
) -> UserModel:
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
    
    if actual_token is None:
        logger.error("Токен не найден ни в куках, ни в заголовке")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден в cookies или заголовке Authorization"
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        logger.info(f"Декодируем токен: {actual_token[:20]}...")
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.error("В токене отсутствует поле sub")
            raise credentials_exception
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка декодирования токена: {str(e)}")
        raise credentials_exception
    
    user = await UserModel.get_by_id(session, int(user_id))
    if user is None:
        logger.error(f"Пользователь с ID {user_id} не найден")
        raise credentials_exception
        
    return user


conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD'),
    MAIL_FROM = os.getenv('MAIL_FROM'),
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465)),
    MAIL_SERVER = os.getenv('MAIL_SERVER'),
    MAIL_STARTTLS = os.getenv('MAIL_STARTTLS', 'False').lower() == 'true',
    MAIL_SSL_TLS = os.getenv('MAIL_SSL_TLS', 'True').lower() == 'true'
)

async def send_activation_email(email_to: str, activation_link: str):
    try:
        message = MessageSchema(
            subject="Подтверждение регистрации",
            recipients=[email_to],
            body=f"""
            Спасибо за регистрацию!
            Для активации аккаунта перейдите по ссылке:
            {activation_link}
            """,
            subtype="plain"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
    except Exception as e:
        print(f"Ошибка при отправке email: {str(e)}")
        # Здесь можно добавить логирование ошибки

@router.post("/register", response_model=UserReadShema, status_code=status.HTTP_201_CREATED, summary="Регистрация")
async def register(
    user: UserCreateShema,
    background_tasks: BackgroundTasks,
    session: SessionDep
):
    # Проверяем, не зарегистрирован ли уже email
    db_user = await UserModel.get_by_email(session, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    
    # Подготавливаем данные
    hashed_password = await get_password_hash(user.password)
    activation_token = secrets.token_urlsafe(32)
    
    try:
        # Создаем пользователя
        new_user = UserModel(
            first_name = user.first_name,
            last_name = user.last_name,
            email = user.email,
            hashed_password = hashed_password,
            is_active = False,
            activation_token = activation_token
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        # Используем Celery для отправки письма (импортируем здесь, чтобы избежать циклических импортов)
        from app.services.email_service import send_verification_email
        
        # Формируем ссылку активации
        activation_link = f"http://localhost:3000/activate/{activation_token}"
        
        # Отправляем задачу через Celery
        celery_task_id = send_verification_email(
            str(new_user.id), 
            user.email, 
            activation_link
        )
        
        # Для отладки записываем ID задачи Celery
        if celery_task_id:
            logger.info(f"Отправка email активации через Celery, task_id: {celery_task_id}")
        else:
            logger.warning(f"Не удалось отправить email активации через Celery для пользователя {new_user.id}")
            
            # Запасной вариант - отправляем напрямую
            background_tasks.add_task(
                send_activation_email,
                email_to=user.email,
                activation_link=activation_link
            )
        
        return UserReadShema(
            id = new_user.id,
            first_name = new_user.first_name,
            last_name = new_user.last_name,
            email = new_user.email,
        )
        
    except Exception as e:
        # Если произошла ошибка, откатываем изменения
        await session.rollback()
        logger.error(f"Ошибка при регистрации: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        )

@router.post("/login", response_model=TokenShema, summary="Вход")
async def login(
    session: SessionDep, 
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    response: Response = None
):
    user = await UserModel.get_by_email(session, form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not await verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Пожалуйста, подтвердите свой email"
        )
    
    # Получаем информацию о пользовательской сессии
    user_agent = request.headers.get("user-agent", "Unknown")
    client_ip = request.client.host if request.client else "Unknown"
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user.id),
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active
    }
    
    # Получаем токен и его jti
    access_token, jti = await create_access_token(data=token_data, expires_delta=access_token_expires)
    
    # Запись информации о сессии
    await log_user_session(session, user.id, jti, user_agent, client_ip)
    
    # Обновление даты последнего входа
    await update_last_login(session, user.id)
    
    # Устанавливаем cookie с улучшенными настройками безопасности
    secure = os.getenv("ENVIRONMENT", "development") != "development"  # Secure только в production
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="Lax",  # Меняем на Lax для кросс-доменных запросов
        secure=False,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", summary="Выход из системы")
async def logout(
    response: Response, 
    session: SessionDep,
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
):
    # Пробуем получить токен сначала из куки, потом из заголовка
    if token is None and authorization:
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    if token:
        try:
            # Декодируем токен для получения jti
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            
            # Если в токене есть jti, отзываем сессию
            if jti:
                from models import UserSessionModel
                await UserSessionModel.revoke_session(session, jti, "User logout")
                logger.info(f"Сессия с JTI {jti} отозвана при выходе")
        except Exception as e:
            logger.error(f"Ошибка при отзыве сессии: {str(e)}")
    
    # Удаляем куки в любом случае
    response.delete_cookie(key="access_token")
    return {"status": "success", "message": "Успешный выход из системы"}

@router.get("/users/me/sessions", summary="Получение списка активных сессий пользователя")
async def get_user_sessions(session: SessionDep, current_user: UserModel = Depends(get_current_user)):
    """
    Возвращает список активных сессий пользователя.
    """
    try:
        from models import UserSessionModel
        from sqlalchemy import select
        
        # Получаем активные сессии пользователя
        query = select(UserSessionModel).filter(
            UserSessionModel.user_id == current_user.id,
            UserSessionModel.is_active == True
        ).order_by(UserSessionModel.created_at.desc())
        
        result = await session.execute(query)
        sessions = result.scalars().all()
        
        session_data = []
        for user_session in sessions:
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
):
    """
    Отзывает указанную сессию пользователя.
    """
    try:
        from models import UserSessionModel
        
        # Проверяем, существует ли сессия и принадлежит ли она пользователю
        query = select(UserSessionModel).filter(
            UserSessionModel.id == session_id,
            UserSessionModel.user_id == current_user.id
        )
        
        result = await session.execute(query)
        user_session = result.scalars().first()
        
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия не найдена или не принадлежит пользователю"
            )
        
        # Отзываем сессию
        user_session.is_active = False
        user_session.revoked_at = datetime.now(timezone.utc)
        user_session.revoked_reason = "Revoked by user"
        
        await session.commit()
        
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
):
    """
    Отзывает все активные сессии пользователя, кроме текущей.
    """
    try:
        # Получаем текущий JTI из токена
        current_jti = None
        if token is None and authorization:
            token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_jti = payload.get("jti")
        
        # Отзываем все сессии, кроме текущей
        from models import UserSessionModel
        revoked_count = await UserSessionModel.revoke_all_user_sessions(
            session, current_user.id, exclude_jti=current_jti
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
        from schema import UserReadShema
        return UserReadShema(**base_data)

@router.get("/activate/{token}")
async def activate_user(token: str, session: SessionDep, response: Response):
    user = await UserModel.get_by_activation_token(session, token)
    
    if not user:
        raise HTTPException(status_code=400, detail="Недействительный токен активации")
    
    await user.activate(session)
    
    # Создаем токен доступа
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user.id),
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active
    }
    access_token = await create_access_token(data=token_data, expires_delta=access_token_expires)
    
    # Устанавливаем cookie
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    
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
):
    """
    Смена пароля пользователя.
    
    - **current_password**: Текущий пароль
    - **new_password**: Новый пароль
    """
    # Проверяем текущий пароль
    if not await verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Хешируем новый пароль
    hashed_password = await get_password_hash(password_data.new_password)
    
    # Обновляем пароль пользователя
    current_user.hashed_password = hashed_password
    session.add(current_user)
    await session.commit()
    
    return {"status": "success", "message": "Пароль успешно изменен"}

async def log_user_session(session: AsyncSession, user_id: int, jti: str, user_agent: str, client_ip: str):
    """
    Записывает информацию о новой сессии пользователя.
    """
    try:
        # Создаем запись о сессии
        new_session = UserSessionModel(
            user_id=user_id,
            jti=jti,
            user_agent=user_agent,
            ip_address=client_ip,
            is_active=True,  # Сессия активна при создании
            created_at=datetime.now(timezone.utc)
        )
        
        session.add(new_session)
        await session.commit()
        
        logger.info(f"Создана новая сессия для пользователя {user_id} с JTI {jti}")
        
        # Проверяем, нужно ли отправить уведомление о новом входе
        await check_and_notify_suspicious_login(session, user_id, client_ip, user_agent)
        
    except Exception as e:
        logger.error(f"Ошибка при записи сессии: {str(e)}")
        # Не выбрасываем исключение, чтобы не прерывать процесс логина

async def update_last_login(session: AsyncSession, user_id: int):
    try:
        user = await UserModel.get_by_id(session, user_id)
        if user:
            # Убираем timezone для совместимости с БД
            user.last_login = datetime.now().replace(tzinfo=None)
            await session.commit()
            logger.info(f"Обновлена дата последнего входа для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении даты последнего входа: {str(e)}")

async def check_and_notify_suspicious_login(session: AsyncSession, user_id: int, client_ip: str, user_agent: str):
    """
    Проверяет, является ли вход подозрительным, и отправляет уведомление при необходимости.
    """
    try:
        # Получаем предыдущие сессии пользователя
        stmt = select(UserSessionModel).filter(
            UserSessionModel.user_id == user_id,
            UserSessionModel.is_active == True
        ).order_by(UserSessionModel.created_at.desc()).limit(5)
        
        result = await session.execute(stmt)
        previous_sessions = result.scalars().all()
        
        # Если это первый вход или у нас недостаточно данных, просто записываем сессию
        if len(previous_sessions) <= 1:
            return
        
        # Проверяем, отличается ли IP адрес от обычного
        known_ips = set(session.ip_address for session in previous_sessions if session.ip_address != client_ip)
        
        # Если IP новый, отправляем уведомление
        if client_ip not in known_ips and len(known_ips) > 0:
            user = await UserModel.get_by_id(session, user_id)
            if user and user.email:
                # В реальном приложении здесь будет отправка email
                logger.warning(f"Обнаружен вход с нового IP адреса для пользователя {user_id}: {client_ip}")
                # await send_suspicious_login_email(user.email, client_ip, user_agent)
    
    except Exception as e:
        logger.error(f"Ошибка при проверке подозрительного входа: {str(e)}")

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
    # Логирование для отладки
    logger.info(f"Запрос проверки разрешений для пользователя ID={current_user.id}, permission={permission}")
    
    # Базовые пермиссии на основе статуса пользователя
    result = {
        "is_authenticated": True,
        "is_active": current_user.is_active,
        "is_admin": current_user.is_admin,
        "is_super_admin": current_user.is_super_admin,
    }
    
    # Если запрошено конкретное разрешение
    if permission:
        # Если суперадмин - у него есть все разрешения
        if current_user.is_super_admin:
            result["has_permission"] = True
            return result
            
        # Проверки для обычных пользователей и админов
        if permission == "read":
            # Для чтения ресурсов обычно нужно быть аутентифицированным
            result["has_permission"] = True
        elif permission in ["write", "update"]:
            # Для записи может потребоваться больше прав
            if resource_type == "user" and resource_id == current_user.id:
                # Пользователь может изменять свой профиль
                result["has_permission"] = True
            elif current_user.is_admin:
                # Админы могут изменять большинство ресурсов
                result["has_permission"] = True
            else:
                result["has_permission"] = False
        elif permission == "delete":
            # Удаление обычно требует админских прав
            result["has_permission"] = current_user.is_admin
        elif permission == "admin_access":
            # Доступ к админ-панели
            result["has_permission"] = current_user.is_admin or current_user.is_super_admin
        elif permission == "super_admin_access":
            # Доступ к функциям суперадмина
            result["has_permission"] = current_user.is_super_admin
        else:
            # Неизвестный тип разрешения
            result["has_permission"] = False
            
    return result