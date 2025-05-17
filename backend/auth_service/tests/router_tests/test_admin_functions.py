"""Тесты для административных функций."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from datetime import timedelta

from router import (
    service_token, create_user_by_admin
)

# Тесты для получения сервисного токена
@pytest.mark.asyncio
async def test_service_token_success():
    """Тест успешного получения сервисного токена"""
    # Данные для тестирования
    grant_type = "client_credentials"
    client_id = "test_client"
    client_secret = "test_secret"
    
    # Патчим необходимые объекты и функции
    with patch('router.SERVICE_CLIENTS', {"test_client": "test_secret"}), \
         patch('router.TokenService.create_access_token', new_callable=AsyncMock) as mock_create_token:
        
        # Настраиваем поведение мока
        mock_create_token.return_value = ("service_token", "jti")
        
        # Вызываем тестируемую функцию
        result = await service_token(
            grant_type=grant_type,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Проверяем результат
        assert result["access_token"] == "service_token"
        assert result["token_type"] == "bearer"
        
        # Проверяем вызов функции
        mock_create_token.assert_called_once()
        args, kwargs = mock_create_token.call_args
        assert args[0] == {"sub": "test_client", "scope": "service"}
        assert isinstance(kwargs["expires_delta"], timedelta)

@pytest.mark.asyncio
async def test_service_token_invalid_grant_type():
    """Тест получения токена с неверным типом гранта"""
    # Данные для тестирования
    grant_type = "password"  # Неверный тип гранта
    client_id = "test_client"
    client_secret = "test_secret"
    
    # Проверяем, что функция вызывает исключение
    with pytest.raises(HTTPException) as exc_info:
        await service_token(
            grant_type=grant_type,
            client_id=client_id,
            client_secret=client_secret
        )
    
    # Проверяем исключение
    assert exc_info.value.status_code == 400
    assert "Unsupported grant_type" in exc_info.value.detail

@pytest.mark.asyncio
async def test_service_token_invalid_credentials():
    """Тест получения токена с неверными учетными данными"""
    # Данные для тестирования
    grant_type = "client_credentials"
    client_id = "test_client"
    client_secret = "wrong_secret"
    
    # Патчим SERVICE_CLIENTS
    with patch('router.SERVICE_CLIENTS', {"test_client": "correct_secret"}):
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await service_token(
                grant_type=grant_type,
                client_id=client_id,
                client_secret=client_secret
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 401
        assert "Invalid client credentials" in exc_info.value.detail

# Тесты для создания пользователя администратором
@pytest.mark.asyncio
async def test_create_user_by_admin_success(mock_session, mock_super_admin_user):
    """Тест успешного создания пользователя администратором"""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.first_name = "New"
    user_data.last_name = "User"
    user_data.email = "newuser@example.com"
    user_data.password = "Password123"
    user_data.personal_data_agreement = True
    user_data.notification_agreement = True
    
    # Мок результата создания пользователя
    new_user = MagicMock()
    new_user.id = 10
    new_user.first_name = "New"
    new_user.last_name = "User"
    new_user.email = "newuser@example.com"
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.create_user', new_callable=AsyncMock) as mock_create_user, \
         patch('router.UserReadSchema') as mock_schema:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = None  # Пользователь не существует
        mock_create_user.return_value = (new_user, None)  # Успешное создание пользователя
        mock_result = MagicMock()
        mock_schema.return_value = mock_result
        
        # Вызываем тестируемую функцию
        result = await create_user_by_admin(
            user=user_data, 
            session=mock_session, 
            is_admin=True,
            current_user=mock_super_admin_user
        )
        
        # Проверяем результат
        assert result == mock_result
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, user_data.email)
        mock_create_user.assert_called_once_with(
            mock_session,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password=user_data.password,
            is_active=True,
            is_admin=True,
            personal_data_agreement=True,
            notification_agreement=True
        )
        mock_schema.assert_called_once()

@pytest.mark.asyncio
async def test_create_user_by_admin_existing_email(mock_session, mock_super_admin_user):
    """Тест создания пользователя с уже существующим email"""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.email = "existing@example.com"
    
    # Мок существующего пользователя
    existing_user = MagicMock()
    existing_user.email = "existing@example.com"
    
    # Патчим сервис получения пользователя
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = existing_user  # Пользователь уже существует
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await create_user_by_admin(
                user=user_data, 
                session=mock_session, 
                current_user=mock_super_admin_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Email уже зарегистрирован" in exc_info.value.detail 