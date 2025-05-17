"""Финальные тесты для достижения 100% покрытия router.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

# Тесты для получения пустого списка сессий - строки 519-520, 533
@pytest.mark.asyncio
async def test_get_user_sessions_empty(mock_session, mock_user):
    """Тест получения пустого списка сессий пользователя."""
    # Патчим сервисную функцию
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions:
        # Настраиваем поведение мока - нет сессий
        mock_get_sessions.return_value = []
        
        # Импортируем функцию
        from router import get_user_sessions
        
        # Вызываем тестируемую функцию
        result = await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем результат - должен быть пустой список сессий
        assert result["sessions"] == []
        
        # Проверяем вызов функции
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)

# Тесты для обновления профиля без изменений - строки 583, 627-628, 635, 643
@pytest.mark.asyncio
async def test_update_user_profile_partial(mock_session, mock_user):
    """Тест частичного обновления профиля пользователя (только имя)."""
    # Данные для тестирования
    update_data = MagicMock()
    update_data.first_name = "NewName"
    update_data.last_name = None  # Не обновляем
    update_data.email = None  # Не обновляем
    
    # Сохраняем исходные данные
    original_last_name = mock_user.last_name
    original_email = mock_user.email
    
    # Создаем заглушку для схемы
    schema_instance = MagicMock()
    
    # Патчим сервисные функции
    with patch('router.user_service.get_user_by_id', new_callable=AsyncMock) as mock_get_by_id, \
         patch('router.UserReadSchema', return_value=schema_instance):
        
        # Настраиваем поведение моков
        mock_get_by_id.return_value = mock_user
        
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
        assert mock_user.first_name == "NewName"
        assert mock_user.last_name == original_last_name  # Не изменилось
        assert mock_user.email == original_email  # Не изменилось
        
        # Проверяем вызовы функций
        mock_session.commit.assert_called_once()
        mock_get_by_id.assert_called_once_with(mock_session, mock_user.id)

# Тесты для сброса пароля - покрытие строк 704-717, 730-731
@pytest.mark.asyncio
async def test_reset_password_mismatch_passwords(mock_session):
    """Тест сброса пароля с несовпадающими паролями."""
    # Данные для тестирования
    reset_data = MagicMock()
    reset_data.token = "valid_token"
    reset_data.new_password = "NewPassword123"
    reset_data.confirm_password = "DifferentPassword456"  # Не совпадает
    
    # Мок для пользователя
    user = MagicMock()
    user.reset_token = "valid_token"
    
    # Патчим сервисные функции
    with patch('models.UserModel.get_by_reset_token', new_callable=AsyncMock) as mock_get_user:
        # Настраиваем поведение мока
        mock_get_user.return_value = user
        
        # Импортируем функцию напрямую
        from router import reset_password
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(data=reset_data, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 400
        assert "Пароли не совпадают" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_user.assert_called_once_with(mock_session, reset_data.token)

# Дополнительный тест для проверки ошибки при получении списка сессий
@pytest.mark.asyncio
async def test_get_user_sessions_error_handling(mock_session, mock_user):
    """Тест обработки ошибки при получении списка сессий."""
    # Патчим сервисную функцию
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions, \
         patch('router.logger') as mock_logger:
        
        # Настраиваем поведение мока - вызываем исключение
        mock_get_sessions.side_effect = Exception("Database error")
        
        # Импортируем функцию
        from router import get_user_sessions
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Ошибка при получении информации о сессиях" in exc_info.value.detail
        
        # Проверяем вызовы функций
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)
        mock_logger.error.assert_called_once() 