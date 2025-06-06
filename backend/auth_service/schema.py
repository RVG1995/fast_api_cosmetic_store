"""Схемы Pydantic для аутентификации и управления пользователями."""

import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, field_validator

class UserCreateShema(BaseModel):
    """Схема для создания нового пользователя."""
    first_name: str = Field(...,min_length=2,max_length=50, description="Имя")
    last_name: str = Field(...,min_length=2,max_length=50, description="Фамилия")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100, description="Пароль")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Подтверждение пароля")
    personal_data_agreement: bool = Field(..., description="Согласие на обработку персональных данных")
    notification_agreement: bool = Field(..., description="Согласие на получение уведомлений")
    
    @model_validator(mode="after")
    def check_passwords_match(cls, model: "UserCreateShema") -> "UserCreateShema":
        """Проверяет совпадение паролей при создании пользователя."""
        if model.password != model.confirm_password:
            raise ValueError("Пароли не совпадают")
        return model
    

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Проверяет сложность пароля."""
        if not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        return value


class UserReadSchema(BaseModel):
    """Схема для чтения данных пользователя."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    
# Отдельная схема для админ-данных, включающая административные поля
class AdminUserReadShema(UserReadSchema):
    """Схема для чтения данных администратора."""
    is_active: bool 
    is_admin: bool
    is_super_admin: bool

class TokenSchema(BaseModel):
    """Схема для токена доступа."""
    access_token: str
    token_type: str

class TokenDataShema(BaseModel):
    """Схема для данных токена."""
    email: Optional[str] = None

class PasswordChangeSchema(BaseModel):
    """Схема для смены пароля пользователя."""
    current_password: str = Field(..., min_length=1, description="Текущий пароль")
    new_password: str = Field(..., min_length=8, max_length=100, description="Новый пароль")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Подтверждение нового пароля")
    
    @model_validator(mode="after")
    def check_passwords_match(cls, model: "PasswordChangeSchema") -> "PasswordChangeSchema":
        """Проверяет совпадение паролей при смене пароля."""
        if model.new_password != model.confirm_password:
            raise ValueError("Новый пароль и подтверждение не совпадают")
        
        if model.new_password == model.current_password:
            raise ValueError("Новый пароль должен отличаться от текущего")
            
        return model
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Проверяет сложность нового пароля."""
        if not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        return value

class UserSessionSchema(BaseModel):
    """Схема для сессии пользователя."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    jti: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

class UserSessionsResponseSchema(BaseModel):
    """Схема для ответа со списком сессий."""
    sessions: List[UserSessionSchema]

class UserSessionStatusSchema(BaseModel):
    """Схема статуса операции с сессией."""
    status: str
    message: str
    revoked_count: Optional[int] = None

class UserUpdateSchema(BaseModel):
    """Схема для обновления данных пользователя."""
    first_name: Optional[str] = Field(None, min_length=2, max_length=50, description="Имя")
    last_name: Optional[str] = Field(None, min_length=2, max_length=50, description="Фамилия")
    email: Optional[EmailStr] = None

class PermissionResponseSchema(BaseModel):
    """Схема для ответа с проверкой разрешений."""
    is_authenticated: bool
    is_active: bool
    is_admin: bool
    is_super_admin: bool
    has_permission: Optional[bool] = None

class PasswordResetRequestSchema(BaseModel):
    """Схема для запроса сброса пароля."""
    email: EmailStr

class PasswordResetSchema(BaseModel):
    """Схема для сброса пароля."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
