from pydantic import BaseModel, ConfigDict,EmailStr,Field, model_validator, field_validator
import re
from typing import Optional

class UserCreateShema(BaseModel):
    first_name: str = Field(...,min_length=2,max_length=50, description="Имя")
    last_name: str = Field(...,min_length=2,max_length=50, description="Фамилия")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100, description="Пароль")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Подтверждение пароля")
    
    @model_validator(mode="after")
    def check_passwords_match(cls, model: "UserCreateShema") -> "UserCreateShema":
        if model.password != model.confirm_password:
            raise ValueError("Пароли не совпадают")
        return model
    

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        return value


class UserReadShema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    
# Отдельная схема для админ-данных, включающая административные поля
class AdminUserReadShema(UserReadShema):
    is_active: bool 
    is_admin: bool
    is_super_admin: bool

class TokenShema(BaseModel):
    access_token: str
    token_type: str

class TokenDataShema(BaseModel):
    email: Optional[str] = None