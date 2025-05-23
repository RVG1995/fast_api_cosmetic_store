"""Тесты для модуля аутентификации и авторизации пользователей (router.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
import jwt

from router import router, register, login, logout, verify_service_jwt, get_all_admins, get_all_users
from models import UserModel

# Тесты для регистрации
@pytest.mark.asyncio
async def test_register_success(mock_session):
    """Тест успешной регистрации пользователя"""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.first_name = "Test"
    user_data.last_name = "User"
    user_data.email = "test@example.com"
    user_data.password = "Password123"
    user_data.personal_data_agreement = True
    user_data.notification_agreement = True
    
    # Мок результата создания пользователя
    new_user = MagicMock()
    new_user.id = 1
    new_user.first_name = "Test"
    new_user.last_name = "User"
    new_user.email = "test@example.com"
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.create_user', new_callable=AsyncMock) as mock_create_user, \
         patch('router.user_service.send_activation_email', new_callable=AsyncMock) as mock_send_email:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = None  # Пользователь не существует
        mock_create_user.return_value = (new_user, "activation_token")  # Успешное создание пользователя
        
        # Вызываем тестируемую функцию
        result = await register(user=user_data, session=mock_session)
        
        # Проверяем результат
        assert result.id == 1
        assert result.email == "test@example.com"
        assert result.first_name == "Test"
        assert result.last_name == "User"
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, user_data.email)
        mock_create_user.assert_called_once()
        mock_send_email.assert_called_once()

@pytest.mark.asyncio
async def test_register_existing_email(mock_session):
    """Тест регистрации с уже существующим email"""
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
            await register(user=user_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Email уже зарегистрирован" in exc_info.value.detail

# Тесты для входа в систему
@pytest.mark.asyncio
async def test_login_success(mock_session):
    """Тест успешного входа в систему"""
    # Создаем данные для тестирования
    form_data = MagicMock()
    form_data.username = "user@example.com"
    form_data.password = "Password123"
    
    # Мок для Request и Response
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "Test Browser"}
    
    response = MagicMock()
    
    # Мок для пользователя
    user = MagicMock()
    user.id = 1
    user.email = "user@example.com"
    user.is_admin = False
    user.is_super_admin = False
    user.is_active = True
    
    # Патчим сервисные функции
    with patch('router.bruteforce_protection.check_ip_blocked', new_callable=AsyncMock) as mock_check_ip, \
         patch('router.user_service.verify_credentials', new_callable=AsyncMock) as mock_verify_creds, \
         patch('router.bruteforce_protection.reset_attempts', new_callable=AsyncMock) as mock_reset_attempts, \
         patch('router.TokenService.create_access_token', new_callable=AsyncMock) as mock_create_token, \
         patch('router.session_service.create_session', new_callable=AsyncMock) as mock_create_session, \
         patch('router.user_service.update_last_login', new_callable=AsyncMock) as mock_update_login:
        
        # Настраиваем поведение моков
        mock_check_ip.return_value = False  # IP не заблокирован
        mock_verify_creds.return_value = user  # Учетные данные верны
        mock_create_token.return_value = ("test_token", "test_jti")  # Успешное создание токена
        
        # Вызываем тестируемую функцию
        result = await login(session=mock_session, request=request, form_data=form_data, response=response)
        
        # Проверяем результат
        assert result["access_token"] == "test_token"
        assert result["token_type"] == "bearer"
        
        # Проверяем вызовы функций
        mock_check_ip.assert_called_once_with("127.0.0.1")
        mock_verify_creds.assert_called_once_with(mock_session, form_data.username, form_data.password)
        mock_reset_attempts.assert_called_once_with("127.0.0.1", form_data.username)
        mock_create_token.assert_called_once()
        mock_create_session.assert_called_once()
        mock_update_login.assert_called_once_with(mock_session, user.id)
        
        # Проверяем, что cookie был установлен
        response.set_cookie.assert_called_once()

@pytest.mark.asyncio
async def test_login_invalid_credentials(mock_session):
    """Тест входа с неверными учетными данными"""
    # Создаем данные для тестирования
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
        mock_record_attempt.return_value = {"blocked": False, "attempts": 1}  # Запись неудачной попытки
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await login(session=mock_session, request=request, form_data=form_data)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 401
        assert "Неверный email или пароль" in exc_info.value.detail
        
        # Проверяем вызовы функций
        mock_check_ip.assert_called_once_with("127.0.0.1")
        mock_verify_creds.assert_called_once_with(mock_session, form_data.username, form_data.password)
        mock_record_attempt.assert_called_once_with("127.0.0.1", form_data.username)

@pytest.mark.asyncio
async def test_login_ip_blocked(mock_session):
    """Тест входа с заблокированного IP"""
    # Создаем данные для тестирования
    form_data = MagicMock()
    
    # Мок для Request
    request = MagicMock()
    request.client.host = "127.0.0.1"
    
    # Патчим сервисные функции
    with patch('router.bruteforce_protection.check_ip_blocked', new_callable=AsyncMock) as mock_check_ip:
        # IP заблокирован
        mock_check_ip.return_value = True
        
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as exc_info:
            await login(session=mock_session, request=request, form_data=form_data)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 429
        assert "Слишком много неудачных попыток входа" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_check_ip.assert_called_once_with("127.0.0.1")

# Тесты для выхода из системы
@pytest.mark.asyncio
async def test_logout_success(mock_session):
    """Тест успешного выхода из системы"""
    # Мок для Response
    response = MagicMock()
    
    # Токен из cookie
    token = "test_token"
    
    # Патчим сервисные функции
    with patch('router.TokenService.decode_token', new_callable=AsyncMock) as mock_decode_token, \
         patch('router.session_service.revoke_session_by_jti', new_callable=AsyncMock) as mock_revoke_session:
        
        # Настраиваем поведение моков
        mock_decode_token.return_value = {"jti": "test_jti"}  # Декодированный токен с JTI
        mock_revoke_session.return_value = True  # Успешный отзыв сессии
        
        # Вызываем тестируемую функцию
        result = await logout(response=response, session=mock_session, token=token, authorization=None)
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Успешный выход из системы" in result["message"]
        
        # Проверяем вызовы функций
        mock_decode_token.assert_called_once_with(token)
        mock_revoke_session.assert_called_once_with(mock_session, "test_jti", "User logout")
        response.delete_cookie.assert_called_once_with(key="access_token")

@pytest.mark.asyncio
async def test_logout_with_auth_header(mock_session):
    """Тест выхода из системы с использованием заголовка авторизации"""
    # Мок для Response
    response = MagicMock()
    
    # Авторизационный заголовок вместо cookie
    authorization = "Bearer test_token"
    
    # Патчим сервисные функции
    with patch('router.TokenService.decode_token', new_callable=AsyncMock) as mock_decode_token, \
         patch('router.session_service.revoke_session_by_jti', new_callable=AsyncMock) as mock_revoke_session:
        
        # Настраиваем поведение моков
        mock_decode_token.return_value = {"jti": "test_jti"}  # Декодированный токен с JTI
        mock_revoke_session.return_value = True  # Успешный отзыв сессии
        
        # Вызываем тестируемую функцию
        result = await logout(response=response, session=mock_session, token=None, authorization=authorization)
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Успешный выход из системы" in result["message"]
        
        # Проверяем вызовы функций
        mock_decode_token.assert_called_once_with("test_token")
        mock_revoke_session.assert_called_once_with(mock_session, "test_jti", "User logout")
        response.delete_cookie.assert_called_once_with(key="access_token")

@pytest.mark.asyncio
async def test_logout_invalid_token(mock_session):
    """Тест выхода из системы с невалидным токеном"""
    # Мок для Response
    response = MagicMock()
    
    # Токен из cookie
    token = "invalid_token"
    
    # Патчим сервисные функции
    with patch('router.TokenService.decode_token', side_effect=jwt.InvalidTokenError) as mock_decode_token:
        # Вызываем тестируемую функцию
        result = await logout(response=response, session=mock_session, token=token, authorization=None)
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Успешный выход из системы" in result["message"]
        
        # Проверяем вызовы функций
        mock_decode_token.assert_called_once_with(token)
        response.delete_cookie.assert_called_once_with(key="access_token")

# Тесты для проверки сервисного JWT
@pytest.mark.asyncio
async def test_verify_service_jwt_valid():
    """Тест проверки валидного JWT с правильным scope"""
    # Создаем мок для HTTPAuthorizationCredentials
    mock_cred = MagicMock()
    mock_cred.credentials = "valid_token"
    
    # Патчим decode_token
    with patch('jwt.decode') as mock_decode:
        mock_decode.return_value = {"scope": "service"}
        
        # Вызываем функцию и проверяем результат
        result = await verify_service_jwt(cred=mock_cred)
        assert result is True

@pytest.mark.asyncio
async def test_verify_service_jwt_invalid_scope():
    """Тест проверки JWT с неверным scope"""
    # Создаем мок для HTTPAuthorizationCredentials
    mock_cred = MagicMock()
    mock_cred.credentials = "valid_token_wrong_scope"
    
    # Патчим decode_token
    with patch('jwt.decode') as mock_decode:
        mock_decode.return_value = {"scope": "user"}
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await verify_service_jwt(cred=mock_cred)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 403
        assert "Insufficient scope" in exc_info.value.detail

@pytest.mark.asyncio
async def test_verify_service_jwt_missing_token():
    """Тест проверки отсутствующего JWT"""
    # Создаем мок без токена
    mock_cred = None
    
    # Проверяем, что функция вызывает исключение
    with pytest.raises(HTTPException) as exc_info:
        await verify_service_jwt(cred=mock_cred)
    
    # Проверяем исключение
    assert exc_info.value.status_code == 401
    assert "Missing bearer token" in exc_info.value.detail

# Тесты для получения списка администраторов
@pytest.mark.asyncio
async def test_get_all_admins(mock_session):
    """Тест получения списка администраторов"""
    # Моки для администраторов
    admin1 = MagicMock()
    admin1.email = "admin1@example.com"
    
    admin2 = MagicMock()
    admin2.email = "admin2@example.com"
    
    # Патчим метод класса
    with patch('models.UserModel.get_all_admins', new_callable=AsyncMock) as mock_get_admins, \
         patch('router.verify_service_jwt', new_callable=AsyncMock) as mock_verify_jwt:
        
        # Настраиваем поведение мока
        mock_get_admins.return_value = [admin1, admin2]
        mock_verify_jwt.return_value = True
        
        # Вызываем тестируемую функцию
        result = await get_all_admins(session=mock_session)
        
        # Проверяем результат
        assert len(result) == 2
        assert result[0]["email"] == "admin1@example.com"
        assert result[1]["email"] == "admin2@example.com"
        
        # Проверяем вызов метода
        mock_get_admins.assert_called_once_with(mock_session)

# Тесты для получения списка всех пользователей
@pytest.mark.asyncio
async def test_get_all_users(mock_session, mock_admin_user):
    """Тест получения списка всех пользователей"""
    # Моки для пользователей
    user1 = MagicMock()
    user1.id = 1
    user1.first_name = "User"
    user1.last_name = "One"
    user1.email = "user1@example.com"
    user1.is_active = True
    user1.is_admin = False
    user1.is_super_admin = False
    
    user2 = MagicMock()
    user2.id = 2
    user2.first_name = "User"
    user2.last_name = "Two"
    user2.email = "user2@example.com"
    user2.is_active = True
    user2.is_admin = True
    user2.is_super_admin = False
    
    # Патчим метод класса и зависимость
    with patch('models.UserModel.get_all_users', new_callable=AsyncMock) as mock_get_users, \
         patch('router.get_admin_user', new_callable=AsyncMock) as mock_get_admin:
        
        # Настраиваем поведение моков
        mock_get_users.return_value = [user1, user2]
        mock_get_admin.return_value = mock_admin_user
        
        # Вызываем тестируемую функцию
        result = await get_all_users(session=mock_session)
        
        # Проверяем результат
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["email"] == "user1@example.com"
        assert result[1]["id"] == 2
        assert result[1]["email"] == "user2@example.com"
        assert result[1]["is_admin"] is True
        
        # Проверяем вызов метода
        mock_get_users.assert_called_once_with(mock_session) 