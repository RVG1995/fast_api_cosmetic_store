"""Pydantic схемы для сервиса уведомлений."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class NotificationSettingBase(BaseModel):
    """Базовая схема настроек уведомлений."""
    model_config = ConfigDict(from_attributes=True)
    user_id: int = Field(..., description="ID пользователя", example="user123")
    event_type: str = Field(..., description="Тип события", example="review.created")
    email: str = Field(..., description="Email для уведомлений", example="admin@example.com")
    push_enabled: bool = Field(True, description="Включены push-уведомления")
    email_enabled: bool = Field(True, description="Включены email-уведомления")


class NotificationSettingCreate(NotificationSettingBase):
    """Схема для создания настроек уведомлений."""
    pass


class NotificationSettingUpdate(BaseModel):
    """Схема для обновления настроек уведомлений."""
    model_config = ConfigDict(from_attributes=True)
    push_enabled: Optional[bool] = Field(None, description="Push-уведомления")
    email_enabled: Optional[bool] = Field(None, description="Email-уведомления")


class NotificationSettingResponse(NotificationSettingBase):
    """Схема ответа с настройками уведомлений."""
    id: int = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    model_config = ConfigDict(from_attributes=True) 

class NotificationEvent(BaseModel):
    """Схема события уведомления."""
    event_type: str
    user_id: Optional[int] = None
    order_id: int

class UserNotificationActivation(BaseModel):
    """Схема для активации уведомлений пользователя через сервисный API."""
    user_id: str
    email: str
    is_admin: bool = False
