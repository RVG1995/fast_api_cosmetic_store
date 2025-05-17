"""Финальные тесты для достижения максимального покрытия router.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

# Тест для прямого вызова функций, покрывающих строки 519-520, 533 - список сессий пользователя
@pytest.mark.asyncio
async def test_get_user_sessions_direct(mock_session, mock_user):
    """Тест прямого вызова функции получения сессий пользователя."""
    # Создаем сессии пользователя
    session1 = MagicMock()
    session1.id = 1
    session1.jti = "jti1"
    session1.user_agent = "Chrome"
    session1.ip_address = "127.0.0.1"
    session1.created_at = datetime.now(timezone.utc)
    session1.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    session1.is_active = True
    
    # Патчим напрямую session_service.get_user_sessions
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions:
        # Возвращаем список сессий
        mock_get_sessions.return_value = [session1]
        
        # Импортируем функцию напрямую
        from router import get_user_sessions
        
        # Вызываем тестируемую функцию
        result = await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем результат
        assert len(result["sessions"]) == 1
        assert result["sessions"][0]["id"] == 1
        assert result["sessions"][0]["jti"] == "jti1"
        
        # Проверяем вызов функции
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)

# Тест для покрытия строк 583, 627-628, 635, 643 - обновление профиля пользователя
@pytest.mark.asyncio
async def test_update_user_profile_email_only(mock_session, mock_user):
    """Тест обновления только email пользователя."""
    # Создаем данные для обновления
    update_data = MagicMock()
    update_data.first_name = None
    update_data.last_name = None
    update_data.email = "newemail@example.com"
    
    # Старый email пользователя
    mock_user.email = "oldemail@example.com"
    
    # Схема ответа
    schema_instance = MagicMock()
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_email', new_callable=AsyncMock) as mock_get_by_email, \
         patch('router.user_service.get_user_by_id', new_callable=AsyncMock) as mock_get_by_id, \
         patch('router.UserReadSchema', return_value=schema_instance):
        
        # Настраиваем поведение моков
        mock_get_by_email.return_value = None  # Email не существует у других пользователей
        mock_get_by_id.return_value = mock_user
        
        # Импортируем функцию напрямую
        from router import update_user_profile
        
        # Вызываем тестируемую функцию
        result = await update_user_profile(
            update_data=update_data,
            session=mock_session,
            current_user=mock_user
        )
        
        # Проверяем результат
        assert result == schema_instance
        
        # Проверяем обновление email
        assert mock_user.email == "newemail@example.com"
        
        # Проверяем вызовы функций - вызов может быть неоднократным
        assert mock_get_by_email.call_count >= 1
        assert mock_get_by_email.call_args_list[0][0][1] == "newemail@example.com"
        mock_session.commit.assert_called_once()
        assert mock_get_by_id.call_count >= 1

# Тест для покрытия строк 704-717, 730-731 - сброс пароля
@pytest.mark.asyncio
async def test_reset_password_invalid_user(mock_session):
    """Тест сброса пароля с неверным токеном (пользователь не имеет токена)."""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "valid_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "NewPassword123"
    
    # Мок для пользователя с пустым токеном
    user = MagicMock()
    user.id = 1
    user.reset_token = None  # Токен не установлен
    
    # Патчим сервисные функции
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user:
        # Пользователь найден, но у него нет токена
        mock_get_user.return_value = user
        
        # Импортируем функцию напрямую
        from router import reset_password
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Неверный или истёкший токен" in exc_info.value.detail 