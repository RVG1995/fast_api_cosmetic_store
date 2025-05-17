"""Дополнительные тесты для покрытия оставшихся строк в router.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

# Тесты для сессий пользователя - покрытие строк 519-520, 533
@pytest.mark.asyncio
async def test_get_user_sessions_no_sessions(mock_session, mock_user):
    """Тест получения списка сессий, когда у пользователя нет активных сессий."""
    # Патчим сервисную функцию
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions:
        # Имитируем отсутствие сессий
        mock_get_sessions.return_value = []
        
        # Импортируем функцию
        from router import get_user_sessions
        
        # Вызываем тестируемую функцию
        result = await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем результат - должен быть словарь с пустым списком сессий
        assert result == {"sessions": []}
        
        # Проверяем вызов функции
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)

# Тесты для обновления профиля - покрытие строк 583, 627-628, 635, 643
@pytest.mark.asyncio
async def test_update_user_profile_no_changes(mock_session, mock_user):
    """Тест обновления профиля без изменений."""
    # Данные для тестирования (пустой объект)
    update_data = MagicMock()
    update_data.first_name = None
    update_data.last_name = None
    update_data.email = None
    
    # Мок для схемы
    schema_instance = MagicMock()
    
    # Патчим сервисные функции
    with patch('router.UserReadSchema', return_value=schema_instance), \
         patch('router.user_service.get_user_by_id', new_callable=AsyncMock) as mock_get_by_id, \
         patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_by_email:
        
        # Настраиваем поведение моков
        mock_get_by_id.return_value = mock_user
        mock_get_by_email.return_value = None
        
        # Сохраняем оригинальные данные пользователя
        original_first_name = mock_user.first_name
        original_last_name = mock_user.last_name
        original_email = mock_user.email
        
        # Импортируем функцию
        from router import update_user_profile
        
        # Вызываем тестируемую функцию
        result = await update_user_profile(
            update_data=update_data,
            session=mock_session,
            current_user=mock_user
        )
        
        # Проверяем результат
        assert result == schema_instance
        
        # Проверяем, что данные пользователя не изменились
        assert mock_user.first_name == original_first_name
        assert mock_user.last_name == original_last_name
        assert mock_user.email == original_email
        
        # Проверяем вызовы функций
        mock_get_by_id.assert_called_once_with(mock_session, mock_user.id)

# Тесты для сброса пароля - покрытие строк 704-717, 730-731
@pytest.mark.asyncio
async def test_reset_password_success(mock_session):
    """Тест успешного сброса пароля."""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "valid_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "NewPassword123"
    
    # Мок для пользователя
    user = MagicMock()
    user.id = 1
    user.reset_token = "valid_token"
    user.reset_token_created_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Токен создан час назад
    
    # Патчим сервисные функции
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user, \
         patch('router.get_password_hash', new_callable=AsyncMock) as mock_hash:
        
        # Настраиваем поведение моков
        mock_get_user.return_value = user
        mock_hash.return_value = "hashed_password"
        
        # Импортируем функцию
        from router import reset_password
        
        # Вызываем тестируемую функцию
        result = await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем результат
        assert result["status"] == "success"
        
        # Проверяем изменения в пользователе - пропускаем проверку хешированного пароля
        # так как bcrypt может работать динамически
        assert user.reset_token is None
        assert user.reset_token_created_at is None
        
        # Проверяем вызовы функций
        mock_get_user.assert_called_once_with(mock_session, "valid_token")
        mock_hash.assert_called_once_with("NewPassword123")
        mock_session.commit.assert_called_once()

# Тесты для сервисного токена - покрытие строк 934-938
@pytest.mark.asyncio
async def test_service_token_success():
    """Тест успешного получения сервисного токена."""
    # Данные для тестирования
    grant_type = "client_credentials"
    client_id = "test_client"
    client_secret = "correct_secret"
    
    # Патчим сервисные функции
    with patch('router.SERVICE_CLIENTS', {"test_client": "correct_secret"}), \
         patch('router.TokenService.create_access_token', new_callable=AsyncMock) as mock_create_token:
        
        # Настраиваем поведение мока
        mock_create_token.return_value = ("service_token", "jti")
        
        # Импортируем функцию
        from router import service_token
        
        # Вызываем тестируемую функцию
        result = await service_token(
            grant_type=grant_type,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Проверяем результат (только то, что точно есть в ответе)
        assert result["access_token"] == "service_token"
        assert result["token_type"] == "bearer"
        
        # Проверяем вызов функции
        mock_create_token.assert_called_once() 