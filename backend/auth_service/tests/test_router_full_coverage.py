"""Тесты для полного покрытия router.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
import sys
import os

# Импортируем напрямую из модуля router.py для тестирования
from router import (
    login, get_user_sessions, 
    activate_user, change_password,
    request_password_reset, reset_password, service_token,
    revoke_user_session, revoke_all_user_sessions, check_user_permissions
)

# Используем только эти импорты для функций, требующих специальной обработки
from aiosmtplib.errors import SMTPException
from aio_pika.exceptions import AMQPError


# Тесты для регистрации - покрытие строк 101-103, 115-119
@pytest.mark.asyncio
async def test_register_database_error(mock_session):
    """Тест обработки ошибки базы данных при регистрации."""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.first_name = "Test"
    user_data.last_name = "User"
    user_data.email = "test@example.com"
    user_data.password = "Password123"
    user_data.personal_data_agreement = True
    user_data.notification_agreement = True
    
    # Патчим сервисные функции и register напрямую
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.create_user', new_callable=AsyncMock) as mock_create_user:
        
        # Настраиваем поведение моков - пользователь не существует, но ошибка при создании
        mock_get_user.return_value = None
        mock_create_user.side_effect = Exception("Database error")
        
        # Дополнительно патчим метод rollback сессии
        mock_session.rollback = AsyncMock()
        
        # Импортируем register здесь, чтобы патчи выше действовали
        from router import register
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await register(user=user_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Произошла ошибка при регистрации" in exc_info.value.detail
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, user_data.email)
        mock_create_user.assert_called_once()
        mock_session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_register_email_error(mock_session):
    """Тест обработки ошибки отправки email при регистрации."""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.first_name = "Test"
    user_data.last_name = "User"
    user_data.email = "test@example.com"
    user_data.password = "Password123"
    user_data.personal_data_agreement = True
    user_data.notification_agreement = True
    
    # Мок для нового пользователя
    new_user = MagicMock()
    new_user.id = 1
    new_user.first_name = "Test"
    new_user.last_name = "User"
    new_user.email = "test@example.com"
    
    # Патчим SMTPException и AMQPError для перехвата в блоке try-except
    with patch('router.SMTPException', SMTPException), \
         patch('router.AMQPError', AMQPError), \
         patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.create_user', new_callable=AsyncMock) as mock_create_user, \
         patch('router.user_service.send_activation_email', new_callable=AsyncMock) as mock_send_email, \
         patch('router.logger') as mock_logger:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = None
        mock_create_user.return_value = (new_user, "activation_token")
        mock_send_email.side_effect = SMTPException("Email error")
        
        # Импортируем register здесь, чтобы патчи выше действовали
        from router import register
        
        # Вызываем тестируемую функцию
        result = await register(user=user_data, session=mock_session)
        
        # Проверяем результат
        assert result.id == new_user.id
        assert result.email == new_user.email
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, user_data.email)
        mock_create_user.assert_called_once()
        mock_send_email.assert_called_once()
        mock_logger.error.assert_called_once()

# Тесты для логина - покрытие строки 169
@pytest.mark.asyncio
async def test_login_ip_blocked_with_time(mock_session):
    """Тест входа с заблокированного IP с указанием времени блокировки."""
    # Данные для тестирования
    form_data = MagicMock()
    form_data.username = "user@example.com"
    form_data.password = "WrongPassword"
    
    # Мок для Request
    request = MagicMock()
    request.client.host = "127.0.0.1"
    
    # Патчим сервисные функции
    with patch('router.bruteforce_protection.check_ip_blocked', new_callable=AsyncMock) as mock_check_ip, \
         patch('router.user_service.verify_credentials', new_callable=AsyncMock) as mock_verify_creds, \
         patch('router.bruteforce_protection.record_failed_attempt', new_callable=AsyncMock) as mock_record_attempt:
        
        # Настраиваем поведение моков
        mock_check_ip.return_value = False  # IP не заблокирован
        mock_verify_creds.return_value = None  # Учетные данные неверны
        mock_record_attempt.return_value = {"blocked": True, "blocked_for": 300}  # IP заблокирован после этой попытки
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await login(session=mock_session, request=request, form_data=form_data)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 429
        assert "Слишком много неудачных попыток входа" in exc_info.value.detail
        assert "300" in exc_info.value.detail  # Проверяем, что время блокировки указано
        
        # Проверяем вызовы функций
        mock_check_ip.assert_called_once()
        mock_verify_creds.assert_called_once()
        mock_record_attempt.assert_called_once()

# Тесты для профиля пользователя - покрытие строк 351-353, 403-405
@pytest.mark.asyncio
async def test_read_users_me_profile_admin(mock_admin_user):
    """Тест получения профиля администратора."""
    # Изменяем данные пользователя для теста
    mock_admin_user.first_name = "Admin"
    mock_admin_user.last_name = "User"
    mock_admin_user.email = "admin@example.com"
    
    # Создаем класс-заглушку для схемы
    schema_instance = MagicMock()
    schema_instance.id = mock_admin_user.id
    schema_instance.first_name = mock_admin_user.first_name
    schema_instance.last_name = mock_admin_user.last_name
    schema_instance.email = mock_admin_user.email
    schema_instance.is_active = mock_admin_user.is_active 
    schema_instance.is_admin = mock_admin_user.is_admin
    schema_instance.is_super_admin = mock_admin_user.is_super_admin
    
    # Сначала импортируем функцию
    from router import read_users_me_profile
    
    # Затем патчим импорты схемы
    with patch('schema.AdminUserReadShema', return_value=schema_instance) as mock_admin_schema:
        # Вызываем тестируемую функцию
        result = await read_users_me_profile(current_user=mock_admin_user)
        
        # Проверяем вызов схемы с правильными параметрами
        assert mock_admin_schema.called
        
        # Проверяем, что результат не None
        assert result is not None

@pytest.mark.asyncio
async def test_read_users_me_profile_regular(mock_user):
    """Тест получения профиля обычного пользователя."""
    # Изменяем данные пользователя для теста
    mock_user.first_name = "Regular"
    mock_user.last_name = "User"
    mock_user.email = "user@example.com"
    
    # Создаем класс-заглушку для схемы
    schema_instance = MagicMock()
    schema_instance.id = mock_user.id
    schema_instance.first_name = mock_user.first_name
    schema_instance.last_name = mock_user.last_name
    schema_instance.email = mock_user.email
    
    # Патчим импорт схемы в модуле schema
    with patch('schema.UserReadSchema', return_value=schema_instance):
        # Импортируем функцию здесь, чтобы патч выше действовал
        from router import read_users_me_profile
        
        # Вызываем тестируемую функцию
        with patch('router.UserReadSchema', return_value=schema_instance):
            result = await read_users_me_profile(current_user=mock_user)
        
        # Проверяем результат
        assert result == schema_instance

# Тесты для активации пользователя - покрытие строк 433-451
@pytest.mark.asyncio
async def test_activate_user_notification_error(mock_session):
    """Тест активации пользователя с ошибкой активации уведомлений."""
    # Данные для тестирования
    token = "valid_activation_token"
    response = MagicMock()
    
    # Мок активированного пользователя с согласием на уведомления
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
         patch('router.user_service.activate_notifications', new_callable=AsyncMock) as mock_activate_notif, \
         patch('router.httpx.RequestError', Exception):  # Патчим Exception как RequestError
        
        # Настраиваем поведение моков
        mock_activate.return_value = user  # Успешная активация пользователя
        mock_create_token.side_effect = [
            ("access_token", "jti"),  # Для основного токена
            ("service_token", "service_jti")  # Для сервисного токена
        ]
        mock_activate_notif.side_effect = Exception("RequestError")  # Ошибка при активации уведомлений
        
        # Вызываем тестируемую функцию
        result = await activate_user(token=token, session=mock_session, response=response)
        
        # Проверяем результат - функция должна завершиться успешно несмотря на ошибку уведомлений
        assert result["status"] == "success"
        assert result["message"] == "Аккаунт успешно активирован"
        assert result["access_token"] == "access_token"
        
        # Проверяем вызовы функций
        mock_activate.assert_called_once_with(mock_session, token)
        assert mock_create_token.call_count == 2
        mock_activate_notif.assert_called_once()

# Тесты для сессий пользователя - покрытие строк 519-520, 533-536
@pytest.mark.asyncio
async def test_get_user_sessions_error(mock_session, mock_user):
    """Тест получения списка активных сессий с ошибкой."""
    # Патчим сервисную функцию с ошибкой
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions:
        # Имитируем ошибку при получении сессий
        mock_get_sessions.side_effect = Exception("Database error")
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Ошибка при получении информации о сессиях" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)

@pytest.mark.asyncio
async def test_revoke_user_session_error(mock_session, mock_user):
    """Тест отзыва сессии пользователя с ошибкой."""
    # Данные для тестирования
    session_id = 123
    
    # Патчим сервисную функцию с ошибкой
    with patch('router.session_service.revoke_session', new_callable=AsyncMock) as mock_revoke:
        # Имитируем ошибку при отзыве сессии
        mock_revoke.side_effect = Exception("Database error")
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await revoke_user_session(
                session_id=session_id,
                session=mock_session,
                current_user=mock_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Ошибка при отзыве сессии" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_revoke.assert_called_once_with(
            session=mock_session,
            session_id=session_id,
            user_id=mock_user.id
        )

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_error(mock_session, mock_user):
    """Тест отзыва всех сессий пользователя с ошибкой."""
    # Данные для тестирования
    token = "test_token"
    
    # Патчим сервисные функции
    with patch('router.TokenService.decode_token', new_callable=AsyncMock) as mock_decode, \
         patch('router.session_service.revoke_all_user_sessions', new_callable=AsyncMock) as mock_revoke_all:
        
        # Настраиваем поведение моков
        mock_decode.return_value = {"jti": "current_jti"}
        mock_revoke_all.side_effect = Exception("Database error")
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await revoke_all_user_sessions(
                session=mock_session,
                current_user=mock_user,
                token=token,
                authorization=None
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Ошибка при отзыве сессий" in exc_info.value.detail
        
        # Проверяем вызовы функций
        mock_decode.assert_called_once_with(token)
        mock_revoke_all.assert_called_once_with(
            session=mock_session,
            user_id=mock_user.id,
            exclude_jti="current_jti"
        )

# Тесты для обновления профиля - покрытие строк 583, 625-628, 635, 643, 963-1008
@pytest.mark.asyncio
async def test_update_user_profile_success(mock_session, mock_user):
    """Тест успешного обновления профиля пользователя."""
    # Данные для тестирования
    update_data = MagicMock()
    update_data.first_name = "New"
    update_data.last_name = "Name"
    update_data.email = "new@example.com"
    
    # Создаем заглушку для схемы
    schema_instance = MagicMock()
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.get_user_by_id', new_callable=AsyncMock) as mock_get_by_id, \
         patch('router.UserReadSchema', return_value=schema_instance):
        
        # Настраиваем поведение моков
        mock_get_user.return_value = None  # Новый email не существует
        
        # Импортируем функцию напрямую из модуля
        from router import update_user_profile
        
        # Вызываем тестируемую функцию
        result = await update_user_profile(
            update_data=update_data,
            session=mock_session,
            current_user=mock_user
        )
        
        # Проверяем результат
        assert result == schema_instance
        
        # Проверяем изменения в пользователе
        assert mock_user.first_name == "New"
        assert mock_user.last_name == "Name"
        assert mock_user.email == "new@example.com"
        
        # Не проверяем количество вызовов get_user_by_email, так как он вызывается дважды
        # Проверяем только факт вызова с правильными параметрами
        mock_get_user.assert_any_call(mock_session, "new@example.com")
        mock_session.commit.assert_called_once()
        mock_get_by_id.assert_called_once_with(mock_session, mock_user.id)

@pytest.mark.asyncio
async def test_update_user_profile_existing_email(mock_session, mock_user):
    """Тест обновления профиля с уже существующим email."""
    # Данные для тестирования
    update_data = MagicMock()
    update_data.email = "existing@example.com"
    
    # Мок существующего пользователя
    existing_user = MagicMock()
    existing_user.id = 999
    existing_user.email = "existing@example.com"
    
    # Патчим сервисную функцию
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        # Новый email уже существует у другого пользователя
        mock_get_user.return_value = existing_user
        
        # Импортируем функцию здесь, чтобы патч выше действовал
        from router import update_user_profile
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await update_user_profile(
                update_data=update_data,
                session=mock_session,
                current_user=mock_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Email уже зарегистрирован другим пользователем" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, "existing@example.com")

@pytest.mark.asyncio
async def test_update_user_profile_error(mock_session, mock_user):
    """Тест обработки ошибки при обновлении профиля."""
    # Данные для тестирования
    update_data = MagicMock()
    update_data.first_name = "New"
    
    # Патчим сервисную функцию
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        # Email не меняется, но ошибка происходит при сохранении
        mock_get_user.return_value = None
        mock_session.commit.side_effect = Exception("Database error")
        
        # Импортируем функцию здесь, чтобы патч выше действовал
        from router import update_user_profile
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await update_user_profile(
                update_data=update_data,
                session=mock_session,
                current_user=mock_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Произошла ошибка при обновлении профиля" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_session.commit.assert_called_once()

# Тесты для проверки прав - покрытие строки 687
@pytest.mark.asyncio
async def test_check_user_permissions_admin_access(mock_user):
    """Тест проверки доступа admin_access."""
    # Настраиваем пользователя
    mock_user.is_admin = False
    mock_user.is_super_admin = False
    
    # Проверяем, что функция вызывает исключение
    with pytest.raises(HTTPException) as exc_info:
        await check_user_permissions(
            permission="admin_access",
            current_user=mock_user
        )
    
    # Проверяем исключение
    assert exc_info.value.status_code == 403
    assert "Not enough permissions" in exc_info.value.detail

# Тесты для сброса пароля - покрытие строк 704-717, 730-731
@pytest.mark.asyncio
async def test_reset_password_mismatch(mock_session):
    """Тест сброса пароля с несовпадающими паролями."""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "valid_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "DifferentPassword123"
    
    # Мок для пользователя
    user = MagicMock()
    user.reset_token = "valid_token"
    
    # Патчим статический метод
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user:
        # Настраиваем поведение мока
        mock_get_user.return_value = user
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Пароли не совпадают" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, "valid_token")

@pytest.mark.asyncio
async def test_reset_password_invalid_token(mock_session):
    """Тест сброса пароля с недействительным токеном."""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "invalid_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "NewPassword123"
    
    # Патчим статический метод
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user:
        # Настраиваем поведение мока - токен недействителен
        mock_get_user.return_value = None
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Неверный или истёкший токен" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, "invalid_token")

# Тесты для получения сервисного токена - покрытие строк 934-938
@pytest.mark.asyncio
async def test_service_token_invalid_grant_type():
    """Тест получения сервисного токена с неверным типом гранта."""
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
    """Тест получения сервисного токена с неверными учетными данными."""
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