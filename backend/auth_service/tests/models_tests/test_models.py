"""Тесты для моделей SQLAlchemy."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

# Добавляем пути импорта для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from models import UserModel, UserSessionModel


@pytest.mark.asyncio
async def test_user_model_get_by_email():
    """Тест получения пользователя по email."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок пользователя
    mock_user = MagicMock(spec=UserModel)
    mock_user.email = "test@example.com"
    
    # Настраиваем возвращаемое значение execute
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserModel.get_by_email(mock_session, "test@example.com")
    
    # Проверяем, что execute был вызван с правильным select запросом
    mock_session.execute.assert_called_once()
    
    # Проверяем, что был вызван scalar_one_or_none
    mock_result.scalar_one_or_none.assert_called_once()
    
    # Проверяем результат
    assert result == mock_user


@pytest.mark.asyncio
async def test_user_model_get_by_activation_token():
    """Тест получения пользователя по токену активации."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок пользователя
    mock_user = MagicMock(spec=UserModel)
    mock_user.activation_token = "test-token"
    
    # Настраиваем возвращаемое значение execute
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserModel.get_by_activation_token(mock_session, "test-token")
    
    # Проверяем, что execute был вызван с правильным select запросом
    mock_session.execute.assert_called_once()
    
    # Проверяем, что был вызван scalar_one_or_none
    mock_result.scalar_one_or_none.assert_called_once()
    
    # Проверяем результат
    assert result == mock_user


@pytest.mark.asyncio
async def test_user_model_get_by_id():
    """Тест получения пользователя по ID."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок пользователя
    mock_user = MagicMock(spec=UserModel)
    mock_user.id = 1
    
    # Настраиваем возвращаемое значение get
    mock_session.get.return_value = mock_user
    
    # Вызываем тестируемый метод
    result = await UserModel.get_by_id(mock_session, 1)
    
    # Проверяем, что get был вызван с правильными аргументами
    mock_session.get.assert_called_once_with(UserModel, 1)
    
    # Проверяем результат
    assert result == mock_user


@pytest.mark.asyncio
async def test_user_model_get_by_reset_token():
    """Тест получения пользователя по токену сброса пароля."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок пользователя
    mock_user = MagicMock(spec=UserModel)
    mock_user.reset_token = "reset-token"
    
    # Настраиваем возвращаемое значение execute
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserModel.get_by_reset_token(mock_session, "reset-token")
    
    # Проверяем, что execute был вызван с правильным select запросом
    mock_session.execute.assert_called_once()
    
    # Проверяем, что был вызван scalar_one_or_none
    mock_result.scalar_one_or_none.assert_called_once()
    
    # Проверяем результат
    assert result == mock_user


@pytest.mark.asyncio
async def test_user_model_get_all_admins():
    """Тест получения всех администраторов."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок пользователей-администраторов
    mock_admin1 = MagicMock(spec=UserModel)
    mock_admin1.is_admin = True
    mock_admin1.is_super_admin = False
    
    mock_admin2 = MagicMock(spec=UserModel)
    mock_admin2.is_admin = True
    mock_admin2.is_super_admin = True
    
    # Настраиваем возвращаемые значения
    # Создаем mock для вложенных вызовов
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [mock_admin1, mock_admin2]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars_result
    
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserModel.get_all_admins(mock_session)
    
    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()
    
    # Проверяем, что scalars был вызван
    mock_result.scalars.assert_called_once()
    
    # Проверяем, что all() был вызван
    mock_scalars_result.all.assert_called_once()
    
    # Проверяем результат
    assert result == [mock_admin1, mock_admin2]


@pytest.mark.asyncio
async def test_user_model_get_all_users():
    """Тест получения всех пользователей."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок пользователей
    mock_user1 = MagicMock(spec=UserModel)
    mock_user2 = MagicMock(spec=UserModel)
    
    # Настраиваем возвращаемые значения
    # Создаем mock для вложенных вызовов
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [mock_user1, mock_user2]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars_result
    
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserModel.get_all_users(mock_session)
    
    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()
    
    # Проверяем, что scalars был вызван
    mock_result.scalars.assert_called_once()
    
    # Проверяем, что all() был вызван
    mock_scalars_result.all.assert_called_once()
    
    # Проверяем результат
    assert result == [mock_user1, mock_user2]


@pytest.mark.asyncio
async def test_user_model_activate():
    """Тест активации пользователя."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем пользователя
    user = UserModel()
    user.is_active = False
    user.activation_token = "activation-token"
    
    # Вызываем тестируемый метод
    await user.activate(mock_session)
    
    # Проверяем, что поля обновились
    assert user.is_active is True
    assert user.activation_token is None
    
    # Проверяем, что commit был вызван
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_session_model_get_by_jti():
    """Тест получения сессии по JTI."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем мок сессии пользователя
    mock_user_session = MagicMock(spec=UserSessionModel)
    mock_user_session.jti = "test-jti"
    
    # Настраиваем возвращаемые значения
    # Создаем mock для вложенных вызовов
    mock_scalars_result = MagicMock()
    mock_scalars_result.first.return_value = mock_user_session
    
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars_result
    
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserSessionModel.get_by_jti(mock_session, "test-jti")
    
    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()
    
    # Проверяем, что scalars был вызван
    mock_result.scalars.assert_called_once()
    
    # Проверяем, что first() был вызван
    mock_scalars_result.first.assert_called_once()
    
    # Проверяем результат
    assert result == mock_user_session


@pytest.mark.asyncio
async def test_user_session_model_revoke_session_success():
    """Тест успешного отзыва сессии."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем фиктивный метод get_by_jti
    test_jti = "test-jti"
    user_session = UserSessionModel()
    user_session.is_active = True
    user_session.revoked_at = None
    user_session.revoked_reason = None
    
    # Патчим метод get_by_jti, чтобы он возвращал наш фиктивный объект
    with patch.object(UserSessionModel, 'get_by_jti', new=AsyncMock(return_value=user_session)):
        # Вызываем тестируемый метод
        result = await UserSessionModel.revoke_session(mock_session, test_jti, "Test reason")
        
        # Проверяем результат
        assert result is True
        
        # Проверяем, что поля в сессии обновились
        assert user_session.is_active is False
        assert user_session.revoked_at is not None
        assert user_session.revoked_reason == "Test reason"
        
        # Проверяем, что commit был вызван
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_session_model_revoke_session_not_found():
    """Тест отзыва несуществующей сессии."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Патчим метод get_by_jti, чтобы он возвращал None
    with patch.object(UserSessionModel, 'get_by_jti', new=AsyncMock(return_value=None)):
        # Вызываем тестируемый метод
        result = await UserSessionModel.revoke_session(mock_session, "non-existent-jti")
        
        # Проверяем результат
        assert result is False
        
        # Проверяем, что commit не был вызван
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_user_session_model_revoke_all_user_sessions():
    """Тест отзыва всех сессий пользователя."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем список фиктивных сессий пользователя
    session1 = UserSessionModel()
    session1.is_active = True
    session1.jti = "jti-1"
    
    session2 = UserSessionModel()
    session2.is_active = True
    session2.jti = "jti-2"
    
    # Настраиваем возвращаемые значения
    # Создаем mock для вложенных вызовов
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [session1, session2]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars_result
    
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод
    result = await UserSessionModel.revoke_all_user_sessions(mock_session, 1)
    
    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()
    
    # Проверяем, что scalars был вызван
    mock_result.scalars.assert_called_once()
    
    # Проверяем, что all() был вызван
    mock_scalars_result.all.assert_called_once()
    
    # Проверяем результат
    assert result == 2
    
    # Проверяем, что сессии были отозваны
    assert session1.is_active is False
    assert session1.revoked_at is not None
    assert session1.revoked_reason == "Revoked by new login/logout"
    
    assert session2.is_active is False
    assert session2.revoked_at is not None
    assert session2.revoked_reason == "Revoked by new login/logout"
    
    # Проверяем, что commit был вызван
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_session_model_revoke_all_user_sessions_with_exclude():
    """Тест отзыва всех сессий пользователя, кроме указанной."""
    # Создаем мок сессии
    mock_session = AsyncMock()
    
    # Создаем список фиктивных сессий пользователя
    session1 = UserSessionModel()
    session1.is_active = True
    session1.jti = "jti-1"
    
    # Настраиваем возвращаемые значения
    # Создаем mock для вложенных вызовов
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [session1]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars_result
    
    mock_session.execute.return_value = mock_result
    
    # Вызываем тестируемый метод с исключением jti-2
    result = await UserSessionModel.revoke_all_user_sessions(mock_session, 1, exclude_jti="jti-2")
    
    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()
    
    # Проверяем, что scalars был вызван
    mock_result.scalars.assert_called_once()
    
    # Проверяем, что all() был вызван
    mock_scalars_result.all.assert_called_once()
    
    # Проверяем результат
    assert result == 1
    
    # Проверяем, что сессия была отозвана
    assert session1.is_active is False
    assert session1.revoked_at is not None
    assert session1.revoked_reason == "Revoked by new login/logout"
    
    # Проверяем, что commit был вызван
    mock_session.commit.assert_called_once()


def test_user_model_repr():
    """Тест метода __repr__ для UserModel."""
    # Создаем пользователя
    user = UserModel()
    user.id = 123
    
    # Проверяем строковое представление
    assert repr(user) == "UserModel(id=123)" 