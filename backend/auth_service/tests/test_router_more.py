"""Тесты для дополнительных функций модуля аутентификации (router.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone

from router import (
    read_users_me_basic, activate_user,
    change_password, check_user_permissions, request_password_reset,
    reset_password, toggle_user_active_status
)
from models import UserModel

# Тесты для получения информации о пользователе
@pytest.mark.asyncio
async def test_read_users_me_basic(mock_user):
    """Тест получения базовой информации о текущем пользователе"""
    # Вызываем тестируемую функцию
    result = await read_users_me_basic(current_user=mock_user)
    
    # Проверяем результат
    assert result["id"] == mock_user.id

# Тесты для активации аккаунта
@pytest.mark.asyncio
async def test_activate_user_success(mock_session):
    """Тест успешной активации аккаунта"""
    # Данные для тестирования
    token = "valid_activation_token"
    response = MagicMock()
    
    # Мок активированного пользователя
    user = MagicMock()
    user.id = 1
    user.email = "user@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_admin = False
    user.is_super_admin = False
    user.is_active = True
    user.notification_agreement = True
    
    # Патчим сервисные функции
    with patch('router.user_service.activate_user', new_callable=AsyncMock) as mock_activate, \
         patch('router.TokenService.create_access_token', new_callable=AsyncMock) as mock_create_token, \
         patch('router.user_service.activate_notifications', new_callable=AsyncMock) as mock_activate_notif:
        
        # Настраиваем поведение моков
        mock_activate.return_value = user  # Успешная активация пользователя
        mock_create_token.side_effect = [
            ("access_token", "jti"),  # Для основного токена
            ("service_token", "service_jti")  # Для сервисного токена
        ]
        mock_activate_notif.return_value = True  # Успешная активация уведомлений
        
        # Вызываем тестируемую функцию
        result = await activate_user(token=token, session=mock_session, response=response)
        
        # Проверяем результат
        assert result["status"] == "success"
        assert result["message"] == "Аккаунт успешно активирован"
        assert result["access_token"] == "access_token"
        assert result["user"]["id"] == 1
        assert result["user"]["email"] == "user@example.com"
        
        # Проверяем вызовы функций
        mock_activate.assert_called_once_with(mock_session, token)
        assert mock_create_token.call_count == 2
        mock_activate_notif.assert_called_once()
        response.set_cookie.assert_called_once()

@pytest.mark.asyncio
async def test_activate_user_invalid_token(mock_session):
    """Тест активации с недействительным токеном"""
    # Данные для тестирования
    token = "invalid_token"
    response = MagicMock()
    
    # Патчим сервисную функцию
    with patch('router.user_service.activate_user', new_callable=AsyncMock) as mock_activate:
        # Недействительный токен
        mock_activate.return_value = None
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await activate_user(token=token, session=mock_session, response=response)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Недействительный токен активации" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_activate.assert_called_once_with(mock_session, token)

# Тесты для смены пароля
@pytest.mark.asyncio
async def test_change_password_success(mock_session, mock_user):
    """Тест успешной смены пароля"""
    # Данные для тестирования
    password_data = MagicMock()
    password_data.current_password = "OldPassword123"
    password_data.new_password = "NewPassword123"
    
    # Патчим сервисные функции
    with patch('router.verify_password', new_callable=AsyncMock) as mock_verify, \
         patch('router.user_service.change_password', new_callable=AsyncMock) as mock_change_pwd:
        
        # Настраиваем поведение моков
        mock_verify.return_value = True  # Текущий пароль верный
        mock_change_pwd.return_value = True  # Пароль успешно изменен
        
        # Вызываем тестируемую функцию
        result = await change_password(
            password_data=password_data,
            session=mock_session,
            current_user=mock_user
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Пароль успешно изменен" in result["message"]
        
        # Проверяем вызовы функций
        mock_verify.assert_called_once_with(password_data.current_password, mock_user.hashed_password)
        mock_change_pwd.assert_called_once_with(
            session=mock_session,
            user_id=mock_user.id,
            new_password=password_data.new_password
        )

@pytest.mark.asyncio
async def test_change_password_wrong_current(mock_session, mock_user):
    """Тест смены пароля с неверным текущим паролем"""
    # Данные для тестирования
    password_data = MagicMock()
    password_data.current_password = "WrongPassword"
    
    # Патчим сервисную функцию
    with patch('router.verify_password', new_callable=AsyncMock) as mock_verify:
        # Текущий пароль неверный
        mock_verify.return_value = False
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await change_password(
                password_data=password_data,
                session=mock_session,
                current_user=mock_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Неверный текущий пароль" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_verify.assert_called_once_with(password_data.current_password, mock_user.hashed_password)

# Тесты для проверки разрешений пользователя
@pytest.mark.asyncio
async def test_check_user_permissions_super_admin(mock_super_admin_user):
    """Тест проверки разрешений суперадминистратора"""
    # Вызываем тестируемую функцию с разными параметрами
    result1 = await check_user_permissions(
        permission="read",
        current_user=mock_super_admin_user
    )
    
    result2 = await check_user_permissions(
        permission="delete",
        resource_type="user",
        resource_id=999,
        current_user=mock_super_admin_user
    )
    
    # Проверяем результаты - суперадмин имеет все права
    assert result1["is_authenticated"] is True
    assert result1["is_super_admin"] is True
    assert result1["has_permission"] is True
    
    assert result2["is_authenticated"] is True
    assert result2["is_super_admin"] is True
    assert result2["has_permission"] is True

@pytest.mark.asyncio
async def test_check_user_permissions_admin(mock_admin_user):
    """Тест проверки разрешений администратора"""
    # Вызываем тестируемую функцию с разными параметрами
    result1 = await check_user_permissions(
        permission="read",
        current_user=mock_admin_user
    )
    
    result2 = await check_user_permissions(
        permission="delete",
        resource_type="user",
        resource_id=999,
        current_user=mock_admin_user
    )
    
    result3 = await check_user_permissions(
        permission="super_admin_access",
        current_user=mock_admin_user
    )
    
    # Проверяем результаты - админ имеет ограниченные права
    assert result1["is_authenticated"] is True
    assert result1["is_admin"] is True
    assert result1["is_super_admin"] is False
    assert result1["has_permission"] is True
    
    assert result2["is_authenticated"] is True
    assert result2["is_admin"] is True
    assert result2["has_permission"] is True
    
    assert result3["is_authenticated"] is True
    assert result3["is_admin"] is True
    assert result3["has_permission"] is False

@pytest.mark.asyncio
async def test_check_user_permissions_regular_user(mock_user):
    """Тест проверки разрешений обычного пользователя"""
    # Обновляем ID пользователя для теста
    mock_user.id = 123
    
    # Вызываем тестируемую функцию с разными параметрами
    result1 = await check_user_permissions(
        permission="read",
        current_user=mock_user
    )
    
    result2 = await check_user_permissions(
        permission="update",
        resource_type="user",
        resource_id=123,  # Свой профиль
        current_user=mock_user
    )
    
    result3 = await check_user_permissions(
        permission="update",
        resource_type="user",
        resource_id=999,  # Чужой профиль
        current_user=mock_user
    )
    
    # Проверяем результаты
    assert result1["is_authenticated"] is True
    assert result1["is_admin"] is False
    assert result1["has_permission"] is True
    
    assert result2["is_authenticated"] is True
    assert result2["is_admin"] is False
    assert result2["has_permission"] is True
    
    assert result3["is_authenticated"] is True
    assert result3["is_admin"] is False
    assert result3["has_permission"] is False

# Тесты для сброса пароля
@pytest.mark.asyncio
async def test_request_password_reset_existing_user(mock_session):
    """Тест запроса сброса пароля для существующего пользователя"""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.email = "user@example.com"
    
    # Мок для пользователя
    user = MagicMock()
    user.id = 1
    user.email = "user@example.com"
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.send_password_reset_email', new_callable=AsyncMock) as mock_send_email, \
         patch('secrets.token_urlsafe') as mock_token:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = user
        mock_token.return_value = "reset_token"
        
        # Вызываем тестируемую функцию
        result = await request_password_reset(data=reset_data, session=mock_session)
        
        # Проверяем результат
        assert result["status"] == "ok"
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, reset_data.email)
        mock_token.assert_called_once_with(32)
        assert user.reset_token == "reset_token"
        assert user.reset_token_created_at is not None
        mock_session.commit.assert_called_once()
        mock_send_email.assert_called_once_with(str(user.id), user.email, "reset_token")

@pytest.mark.asyncio
async def test_request_password_reset_nonexistent_user(mock_session):
    """Тест запроса сброса пароля для несуществующего пользователя"""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.email = "nonexistent@example.com"
    
    # Патчим сервисную функцию
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        # Пользователь не существует
        mock_get_user.return_value = None
        
        # Вызываем тестируемую функцию
        result = await request_password_reset(data=reset_data, session=mock_session)
        
        # Проверяем результат - по соображениям безопасности возвращаем тот же ответ
        assert result["status"] == "ok"
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, reset_data.email)

@pytest.mark.asyncio
async def test_reset_password_success(mock_session):
    """Тест успешного сброса пароля"""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "valid_reset_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "NewPassword123"
    
    # Мок для пользователя
    user = MagicMock()
    user.reset_token = "valid_reset_token"
    
    # Патчим сервисные функции
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user, \
         patch('router.get_password_hash', new_callable=AsyncMock) as mock_hash_pwd:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = user
        mock_hash_pwd.return_value = "hashed_new_password"
        
        # Вызываем тестируемую функцию
        result = await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем результат
        assert result["status"] == "success"
        
        # Проверяем вызовы функций и изменения в пользователе
        mock_get_user.assert_called_once_with(mock_session, reset_data.token)
        mock_hash_pwd.assert_called_once_with(reset_data.new_password)
        assert user.hashed_password == "hashed_new_password"
        assert user.reset_token is None
        assert user.reset_token_created_at is None
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_reset_password_invalid_token(mock_session):
    """Тест сброса пароля с недействительным токеном"""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "invalid_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "NewPassword123"
    
    # Патчим сервисную функцию
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user:
        # Пользователь не найден по токену
        mock_get_user.return_value = None
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Неверный или истёкший токен" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, reset_data.token)

# Тесты для изменения статуса активности пользователя
@pytest.mark.asyncio
async def test_toggle_user_active_status(mock_session, mock_super_admin_user):
    """Тест изменения статуса активности пользователя"""
    # Данные для тестирования
    user_id = 123
    
    # Мок для пользователя
    user = MagicMock()
    user.id = user_id
    user.email = "user@example.com"
    user.is_active = False
    
    # Патчим статический метод
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_user:
        # Настраиваем поведение мока
        mock_get_user.return_value = user
        
        # Вызываем тестируемую функцию
        result = await toggle_user_active_status(
            user_id=user_id,
            session=mock_session,
            current_user=mock_super_admin_user
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Статус активности пользователя" in result["message"]
        assert result["is_active"] is True
        
        # Проверяем вызовы функций и изменения в пользователе
        mock_get_user.assert_called_once_with(mock_session, user_id)
        assert user.is_active is True
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_toggle_user_active_status_not_superadmin(mock_session, mock_admin_user):
    """Тест изменения статуса активности пользователя не суперадмином"""
    # Данные для тестирования
    user_id = 123
    
    # Проверяем, что вызывается исключение
    with pytest.raises(HTTPException) as exc_info:
        await toggle_user_active_status(
            user_id=user_id,
            session=mock_session,
            current_user=mock_admin_user
        )
    
    # Проверяем исключение
    assert exc_info.value.status_code == 403
    assert "Только суперадминистраторы могут изменять статус активности" in exc_info.value.detail

@pytest.mark.asyncio
async def test_toggle_user_active_status_user_not_found(mock_session, mock_super_admin_user):
    """Тест изменения статуса активности несуществующего пользователя"""
    # Данные для тестирования
    user_id = 999
    
    # Патчим статический метод
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_user:
        # Пользователь не найден
        mock_get_user.return_value = None
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await toggle_user_active_status(
                user_id=user_id,
                session=mock_session,
                current_user=mock_super_admin_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, user_id) 