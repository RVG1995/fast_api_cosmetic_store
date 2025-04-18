from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class NotificationSettingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="ID пользователя", example="user123")
    event_type: str = Field(..., description="Тип события", example="review.created")
    email: str = Field(..., description="Email для уведомлений", example="admin@example.com")
    push_enabled: bool = Field(True, description="Включены push-уведомления")
    email_enabled: bool = Field(True, description="Включены email-уведомления")


class NotificationSettingCreate(NotificationSettingBase):
    pass


class NotificationSettingUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    push_enabled: Optional[bool] = Field(None, description="Push-уведомления")
    email_enabled: Optional[bool] = Field(None, description="Email-уведомления")


class NotificationSettingResponse(NotificationSettingBase):
    id: int = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    model_config = ConfigDict(from_attributes=True) 