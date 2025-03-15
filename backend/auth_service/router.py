from fastapi import APIRouter,Depends,Cookie,HTTPException,status,Response, BackgroundTasks
from sqlalchemy import select 
from typing import Optional, Annotated, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database import  get_session
from models import UserModel
import jwt
from schema import TokenShema, UserCreateShema, UserReadShema
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os
from dotenv import load_dotenv
from utils import get_password_hash, verify_password  # Импортируем из utils
from app.services.email_service import send_verification_email
import logging

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
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(
    session: SessionDep, 
    token: str = Cookie(None, alias="access_token"),
    authorization: str = Depends(oauth2_scheme)
) -> UserModel:
    # Пробуем получить токен сначала из куки, потом из заголовка
    if token is None and authorization:
        token = authorization
    
    if token is None:
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Используем новый метод модели
    user = await UserModel.get_by_id(session, int(user_id))
    if user is None:
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
async def login(session: SessionDep, form_data: OAuth2PasswordRequestForm = Depends(), response: Response = None):
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
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user.id),
        "is_admin": user.is_admin,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active
    }
    access_token = await create_access_token(data=token_data, expires_delta=access_token_expires)
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", summary="Выход из системы")
async def logout(response: Response):
    # Устанавливаем пустую cookie с временем жизни 0 секунд
    response.set_cookie(
        key="access_token",
        value="",
        expires=0,
        max_age=0,
        httponly=True,
        samesite='lax'
    )
    return {"message": "Вы успешно вышли из системы"}
    


@router.get("/users/me", response_model=None, summary="Получение данных о текущем пользователе")
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
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