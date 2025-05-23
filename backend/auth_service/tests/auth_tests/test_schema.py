"""Тесты для схем Pydantic в модуле auth_service."""

import pytest
from pydantic import ValidationError

# Импортируем тестируемые схемы
from schema import UserCreateShema, PasswordChangeSchema, UserUpdateSchema


class TestUserCreateSchema:
    """Тесты для схемы создания пользователя."""
    
    def test_valid_user_create_schema(self):
        """Тест валидной схемы создания пользователя."""
        user_data = {
            "first_name": "Иван",
            "last_name": "Иванов", 
            "email": "user@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "personal_data_agreement": True,
            "notification_agreement": True
        }
        
        user = UserCreateShema(**user_data)
        assert user.first_name == "Иван"
        assert user.last_name == "Иванов"
        assert user.email == "user@example.com"
        assert user.password == "Password123"
    
    def test_passwords_mismatch(self):
        """Тест на несовпадающие пароли."""
        user_data = {
            "first_name": "Иван",
            "last_name": "Иванов", 
            "email": "user@example.com",
            "password": "Password123",
            "confirm_password": "DifferentPass456",
            "personal_data_agreement": True,
            "notification_agreement": True
        }
        
        with pytest.raises(ValidationError) as excinfo:
            UserCreateShema(**user_data)
        
        assert "Пароли не совпадают" in str(excinfo.value)
    
    def test_password_without_digits(self):
        """Тест пароля без цифр."""
        user_data = {
            "first_name": "Иван",
            "last_name": "Иванов", 
            "email": "user@example.com",
            "password": "PasswordNoDigits",
            "confirm_password": "PasswordNoDigits",
            "personal_data_agreement": True,
            "notification_agreement": True
        }
        
        with pytest.raises(ValidationError) as excinfo:
            UserCreateShema(**user_data)
        
        assert "Пароль должен содержать хотя бы одну цифру" in str(excinfo.value)
    
    def test_password_without_letters(self):
        """Тест пароля без букв."""
        user_data = {
            "first_name": "Иван",
            "last_name": "Иванов", 
            "email": "user@example.com",
            "password": "12345678",
            "confirm_password": "12345678",
            "personal_data_agreement": True,
            "notification_agreement": True
        }
        
        with pytest.raises(ValidationError) as excinfo:
            UserCreateShema(**user_data)
        
        assert "Пароль должен содержать хотя бы одну букву" in str(excinfo.value)


class TestPasswordChangeSchema:
    """Тесты для схемы смены пароля."""
    
    def test_valid_password_change(self):
        """Тест валидной схемы смены пароля."""
        password_data = {
            "current_password": "OldPass123",
            "new_password": "NewPass456",
            "confirm_password": "NewPass456"
        }
        
        password_change = PasswordChangeSchema(**password_data)
        assert password_change.current_password == "OldPass123"
        assert password_change.new_password == "NewPass456"
    
    def test_new_passwords_mismatch(self):
        """Тест на несовпадающие новые пароли."""
        password_data = {
            "current_password": "OldPass123",
            "new_password": "NewPass456",
            "confirm_password": "DifferentPass789"
        }
        
        with pytest.raises(ValidationError) as excinfo:
            PasswordChangeSchema(**password_data)
        
        assert "Новый пароль и подтверждение не совпадают" in str(excinfo.value)
    
    def test_same_new_and_current_password(self):
        """Тест на совпадение нового и текущего пароля."""
        password_data = {
            "current_password": "SamePass123",
            "new_password": "SamePass123",
            "confirm_password": "SamePass123"
        }
        
        with pytest.raises(ValidationError) as excinfo:
            PasswordChangeSchema(**password_data)
        
        assert "Новый пароль должен отличаться от текущего" in str(excinfo.value)
    
    def test_new_password_without_digits(self):
        """Тест нового пароля без цифр."""
        password_data = {
            "current_password": "OldPass123",
            "new_password": "NewPasswordNoDigits",
            "confirm_password": "NewPasswordNoDigits"
        }
        
        with pytest.raises(ValidationError) as excinfo:
            PasswordChangeSchema(**password_data)
        
        assert "Пароль должен содержать хотя бы одну цифру" in str(excinfo.value)
    
    def test_new_password_without_letters(self):
        """Тест нового пароля без букв."""
        password_data = {
            "current_password": "OldPass123",
            "new_password": "12345678",
            "confirm_password": "12345678"
        }
        
        with pytest.raises(ValidationError) as excinfo:
            PasswordChangeSchema(**password_data)
        
        assert "Пароль должен содержать хотя бы одну букву" in str(excinfo.value)


class TestUserUpdateSchema:
    """Тесты для схемы обновления пользователя."""
    
    def test_all_fields_update(self):
        """Тест обновления всех полей."""
        update_data = {
            "first_name": "Петр",
            "last_name": "Петров",
            "email": "new_email@example.com"
        }
        
        update_schema = UserUpdateSchema(**update_data)
        assert update_schema.first_name == "Петр"
        assert update_schema.last_name == "Петров"
        assert update_schema.email == "new_email@example.com"
    
    def test_partial_update(self):
        """Тест частичного обновления полей."""
        # Только имя
        update_schema = UserUpdateSchema(first_name="Петр")
        assert update_schema.first_name == "Петр"
        assert update_schema.last_name is None
        assert update_schema.email is None
        
        # Только фамилия
        update_schema = UserUpdateSchema(last_name="Петров")
        assert update_schema.first_name is None
        assert update_schema.last_name == "Петров"
        assert update_schema.email is None
        
        # Только email
        update_schema = UserUpdateSchema(email="new_email@example.com")
        assert update_schema.first_name is None
        assert update_schema.last_name is None
        assert update_schema.email == "new_email@example.com"
        
        # Имя и фамилия
        update_schema = UserUpdateSchema(first_name="Петр", last_name="Петров")
        assert update_schema.first_name == "Петр"
        assert update_schema.last_name == "Петров"
        assert update_schema.email is None 