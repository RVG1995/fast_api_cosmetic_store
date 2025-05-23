"""Заключительные тесты для достижения полного покрытия router.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

# Тесты для механизма создания пользователя администратором
@pytest.mark.asyncio
async def test_create_user_by_admin_success(mock_session, mock_super_admin_user):
    """Тест успешного создания пользователя администратором."""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.first_name = "Admin"
    user_data.last_name = "Created"
    user_data.email = "admincreated@example.com"
    user_data.password = "StrongPass123"
    user_data.personal_data_agreement = True
    user_data.notification_agreement = True
    
    # Мок для нового пользователя
    new_user = MagicMock()
    new_user.id = 10
    new_user.first_name = "Admin"
    new_user.last_name = "Created"
    new_user.email = "admincreated@example.com"
    
    # Мок для схемы ответа
    schema_instance = MagicMock()
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.create_user', new_callable=AsyncMock) as mock_create_user, \
         patch('router.UserReadSchema', return_value=schema_instance):
        
        # Настраиваем поведение моков
        mock_get_user.return_value = None  # Email не существует
        mock_create_user.return_value = (new_user, None)  # Успешное создание пользователя
        
        # Импортируем функцию напрямую
        from router import create_user_by_admin
        
        # Вызываем тестируемую функцию
        result = await create_user_by_admin(
            user=user_data,
            session=mock_session,
            is_admin=True,
            current_user=mock_super_admin_user
        )
        
        # Проверяем результат
        assert result == schema_instance
        
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

@pytest.mark.asyncio
async def test_create_user_by_admin_error(mock_session, mock_super_admin_user):
    """Тест обработки ошибки при создании пользователя администратором."""
    # Данные для тестирования
    user_data = MagicMock()
    user_data.email = "newuser@example.com"
    user_data.first_name = "New"
    user_data.last_name = "User"
    user_data.password = "StrongPass123"
    user_data.personal_data_agreement = True
    user_data.notification_agreement = True
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('router.user_service.create_user', new_callable=AsyncMock) as mock_create_user:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = None  # Email не существует
        mock_create_user.side_effect = Exception("Database error")  # Ошибка при создании
        
        # Патчим rollback сессии
        mock_session.rollback = AsyncMock()
        
        # Импортируем функцию напрямую
        from router import create_user_by_admin
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await create_user_by_admin(
                user=user_data,
                session=mock_session,
                current_user=mock_super_admin_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Произошла ошибка при создании пользователя" in exc_info.value.detail
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, user_data.email)
        mock_create_user.assert_called_once()
        mock_session.rollback.assert_called_once()

# Тесты для получения профиля - проверка работы с суперадминистратором
@pytest.mark.asyncio
async def test_read_users_me_profile_super_admin(mock_super_admin_user):
    """Тест получения профиля суперадминистратора."""
    # Изменяем данные пользователя для теста
    mock_super_admin_user.first_name = "Super"
    mock_super_admin_user.last_name = "Admin"
    mock_super_admin_user.email = "superadmin@example.com"
    
    # Мок для схемы
    schema_instance = MagicMock()
    schema_instance.id = mock_super_admin_user.id
    schema_instance.first_name = mock_super_admin_user.first_name
    schema_instance.last_name = mock_super_admin_user.last_name
    schema_instance.email = mock_super_admin_user.email
    schema_instance.is_active = mock_super_admin_user.is_active
    schema_instance.is_admin = mock_super_admin_user.is_admin
    schema_instance.is_super_admin = mock_super_admin_user.is_super_admin
    
    # Патчим импорт схемы
    with patch('schema.AdminUserReadShema', return_value=schema_instance):
        # Импортируем функцию
        from router import read_users_me_profile
        
        # Вызываем тестируемую функцию
        result = await read_users_me_profile(current_user=mock_super_admin_user)
        
        # Проверяем результат
        assert result == schema_instance

# Тесты для блокировки IP адреса
@pytest.mark.asyncio
async def test_login_with_ip_block_and_attempt_info(mock_session):
    """Тест входа с IP адресом, который блокируется после неудачной попытки."""
    # Данные для тестирования
    form_data = MagicMock()
    form_data.username = "user@example.com"
    form_data.password = "WrongPassword"
    
    # Мок для Request
    request = MagicMock()
    request.client.host = "192.168.1.1"
    
    # Патчим сервисные функции
    with patch('router.bruteforce_protection.check_ip_blocked', new_callable=AsyncMock) as mock_check_ip, \
         patch('router.user_service.verify_credentials', new_callable=AsyncMock) as mock_verify_creds, \
         patch('router.bruteforce_protection.record_failed_attempt', new_callable=AsyncMock) as mock_record_attempt:
        
        # Настраиваем поведение моков
        mock_check_ip.return_value = False  # IP еще не заблокирован
        mock_verify_creds.return_value = None  # Учетные данные неверны
        # Блокируем IP после этой попытки и возвращаем время блокировки
        mock_record_attempt.return_value = {
            "blocked": True,
            "blocked_for": 60,
            "attempts": 5,
            "max_attempts": 5
        }
        
        # Импортируем функцию напрямую
        from router import login
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await login(session=mock_session, request=request, form_data=form_data)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 429
        assert "Слишком много неудачных попыток входа" in exc_info.value.detail
        assert "60" in exc_info.value.detail  # Проверяем, что время блокировки указано
        
        # Проверяем вызовы функций
        mock_check_ip.assert_called_once_with("192.168.1.1")
        mock_verify_creds.assert_called_once_with(mock_session, form_data.username, form_data.password)
        mock_record_attempt.assert_called_once_with("192.168.1.1", form_data.username)

# Тесты для активации с уведомлениями
@pytest.mark.asyncio
async def test_activate_user_with_notification_success(mock_session):
    """Тест активации пользователя с успешной активацией уведомлений."""
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
         patch('router.user_service.activate_notifications', new_callable=AsyncMock) as mock_activate_notif:
        
        # Настраиваем поведение моков
        mock_activate.return_value = user  # Успешная активация пользователя
        mock_create_token.side_effect = [
            ("access_token", "jti"),  # Для основного токена
            ("service_token", "service_jti")  # Для сервисного токена
        ]
        mock_activate_notif.return_value = True  # Успешная активация уведомлений
        
        # Импортируем функцию напрямую
        from router import activate_user
        
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

# Тесты для изменения статуса активности пользователя
@pytest.mark.asyncio
async def test_toggle_user_active_status_success(mock_session, mock_super_admin_user):
    """Тест успешного изменения статуса активности пользователя."""
    # Данные для тестирования
    user_id = 123
    
    # Мок для пользователя
    user = MagicMock()
    user.id = user_id
    user.email = "user@example.com"
    user.is_active = False  # Начальное состояние - неактивен
    
    # Патчим метод модели
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_user:
        # Настраиваем мок
        mock_get_user.return_value = user
        
        # Импортируем функцию напрямую
        from router import toggle_user_active_status
        
        # Вызываем тестируемую функцию
        result = await toggle_user_active_status(
            user_id=user_id,
            session=mock_session,
            current_user=mock_super_admin_user
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Статус активности пользователя" in result["message"]
        assert result["is_active"] is True  # Статус должен измениться на противоположный
        
        # Проверяем изменение в объекте пользователя
        assert user.is_active is True
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, user_id)
        mock_session.commit.assert_called_once() 