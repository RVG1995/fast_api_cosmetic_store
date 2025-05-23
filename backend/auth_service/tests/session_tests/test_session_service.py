"""Тесты для модуля управления сессиями (session_service.py)."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

# Импортируем тестируемый модуль
from app.services.auth.session_service import SessionService, session_service
from app.services.auth.cache_service import cache_service
from models import UserSessionModel

# Фикстуры для тестирования
@pytest_asyncio.fixture
async def session_service_instance():
    """Экземпляр сервиса сессий для тестирования."""
    return SessionService()

@pytest_asyncio.fixture
async def mock_user_session():
    """Мок для объекта пользовательской сессии."""
    session = MagicMock(spec=UserSessionModel)
    session.id = 1
    session.user_id = 1
    session.jti = "test-jti-123"
    session.user_agent = "Test User Agent"
    session.ip_address = "127.0.0.1"
    session.is_active = True
    session.created_at = datetime.now(timezone.utc)
    session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    session.revoked_at = None
    session.revoked_reason = None
    return session

# Тесты для create_session
@pytest.mark.asyncio
async def test_create_session_success(mock_session, mock_user):
    """Тест успешного создания сессии пользователя."""
    # Мокаем метод delete кэш-сервиса
    with patch('app.services.auth.cache_service.cache_service.delete', new_callable=AsyncMock) as mock_delete:
        # Настраиваем mock_session для имитации успешного создания сессии
        mock_session.refresh = AsyncMock()
        
        # Создаем тестовые данные
        jti = "test-jti-123"
        user_agent = "Test User Agent"
        ip_address = "127.0.0.1"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        # Вызываем тестируемый метод
        result = await session_service.create_session(
            session=mock_session,
            user_id=mock_user.id,
            jti=jti,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at
        )
        
        # Проверяем, что добавление в сессию произошло
        mock_session.add.assert_called_once()
        # Проверяем, что был сделан коммит
        mock_session.commit.assert_called_once()
        # Проверяем, что был выполнен refresh
        mock_session.refresh.assert_called_once()
        
        # Проверяем, что кэш был инвалидирован
        cache_key = f"get_user_sessions:{mock_user.id}"
        mock_delete.assert_called_once_with(cache_key)
        
        # Проверяем, что результат не None
        assert result is not None
        
        # Проверяем тип добавленного объекта
        added_session = mock_session.add.call_args.args[0]
        assert isinstance(added_session, UserSessionModel)
        assert added_session.user_id == mock_user.id
        assert added_session.jti == jti
        assert added_session.user_agent == user_agent
        assert added_session.ip_address == ip_address
        assert added_session.is_active is True
        assert added_session.expires_at == expires_at

@pytest.mark.asyncio
async def test_create_session_error(mock_session, mock_user):
    """Тест создания сессии при возникновении ошибки."""
    # Мокаем SQLAlchemyError для имитации ошибки
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Создаем тестовые данные
    jti = "test-jti-123"
    user_agent = "Test User Agent"
    ip_address = "127.0.0.1"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    # Вызываем тестируемый метод и проверяем, что он вызывает исключение
    with pytest.raises(SQLAlchemyError):
        await session_service.create_session(
            session=mock_session,
            user_id=mock_user.id,
            jti=jti,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at
        )
    
    # Проверяем, что добавление в сессию произошло
    mock_session.add.assert_called_once()
    # Проверяем, что коммит был вызван
    mock_session.commit.assert_called_once()
    # Проверяем, что refresh не был вызван
    mock_session.refresh.assert_not_called()

# Тесты для get_user_sessions
@pytest.mark.asyncio
async def test_get_user_sessions_success(mock_session, mock_user, mock_user_session):
    """Тест успешного получения сессий пользователя."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_all = MagicMock(return_value=[mock_user_session])
    mock_scalars.scalars.return_value.all = mock_all
    
    # Вызываем тестируемый метод
    result = await session_service.get_user_sessions(
        session=mock_session,
        user_id=mock_user.id
    )
    
    # Проверяем, что был вызван метод execute
    mock_session.execute.assert_called_once()
    
    # Проверяем, что метод вернул список с сессией
    assert len(result) == 1
    assert result[0] == mock_user_session

@pytest.mark.asyncio
async def test_get_user_sessions_error(mock_session, mock_user):
    """Тест получения сессий пользователя при возникновении ошибки."""
    # Мокаем SQLAlchemyError для имитации ошибки
    mock_session.execute.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await session_service.get_user_sessions(
        session=mock_session,
        user_id=mock_user.id
    )
    
    # Проверяем, что метод вернул пустой список при ошибке
    assert result == []

# Тесты для revoke_session
@pytest.mark.asyncio
async def test_revoke_session_success(mock_session, mock_user, mock_user_session):
    """Тест успешного отзыва сессии пользователя."""
    # Мокаем метод delete кэш-сервиса
    with patch('app.services.auth.cache_service.cache_service.delete', new_callable=AsyncMock) as mock_delete:
        # Настраиваем mock_session для имитации успешного запроса
        mock_execute = AsyncMock()
        mock_session.execute = mock_execute
        mock_scalars = MagicMock()
        mock_execute.return_value = mock_scalars
        mock_first = MagicMock(return_value=mock_user_session)
        mock_scalars.scalars.return_value.first = mock_first
        
        # Вызываем тестируемый метод
        result = await session_service.revoke_session(
            session=mock_session,
            session_id=mock_user_session.id,
            user_id=mock_user.id,
            reason="Test revoke"
        )
        
        # Проверяем, что был вызван метод execute
        mock_session.execute.assert_called_once()
        
        # Проверяем, что был сделан коммит
        mock_session.commit.assert_called_once()
        
        # Проверяем, что кэш был инвалидирован
        cache_key = f"get_user_sessions:{mock_user.id}"
        mock_delete.assert_called_once_with(cache_key)
        
        # Проверяем, что метод вернул True
        assert result is True
        
        # Проверяем, что сессия была деактивирована
        assert mock_user_session.is_active is False
        assert mock_user_session.revoked_reason == "Test revoke"
        assert mock_user_session.revoked_at is not None

@pytest.mark.asyncio
async def test_revoke_session_not_found(mock_session, mock_user):
    """Тест отзыва сессии, которая не найдена."""
    # Настраиваем mock_session для имитации отсутствия сессии
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_first = MagicMock(return_value=None)
    mock_scalars.scalars.return_value.first = mock_first
    
    # Вызываем тестируемый метод
    result = await session_service.revoke_session(
        session=mock_session,
        session_id=999,
        user_id=mock_user.id
    )
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что коммит не был вызван
    mock_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_revoke_session_error(mock_session, mock_user, mock_user_session):
    """Тест отзыва сессии при возникновении ошибки."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_first = MagicMock(return_value=mock_user_session)
    mock_scalars.scalars.return_value.first = mock_first
    
    # Мокаем SQLAlchemyError для имитации ошибки при коммите
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await session_service.revoke_session(
        session=mock_session,
        session_id=mock_user_session.id,
        user_id=mock_user.id
    )
    
    # Проверяем, что метод вернул False при ошибке
    assert result is False

# Тесты для revoke_session_by_jti
@pytest.mark.asyncio
async def test_revoke_session_by_jti_success(mock_session, mock_user, mock_user_session):
    """Тест успешного отзыва сессии по JTI."""
    # Мокаем метод delete кэш-сервиса
    with patch('app.services.auth.cache_service.cache_service.delete', new_callable=AsyncMock) as mock_delete:
        # Настраиваем mock_session для имитации успешного запроса
        mock_execute = AsyncMock()
        mock_session.execute = mock_execute
        mock_scalars = MagicMock()
        mock_execute.return_value = mock_scalars
        mock_first = MagicMock(return_value=mock_user_session)
        mock_scalars.scalars.return_value.first = mock_first
        
        # Вызываем тестируемый метод
        result = await session_service.revoke_session_by_jti(
            session=mock_session,
            jti=mock_user_session.jti,
            reason="Test revoke by JTI"
        )
        
        # Проверяем, что был вызван метод execute
        mock_session.execute.assert_called_once()
        
        # Проверяем, что был сделан коммит
        mock_session.commit.assert_called_once()
        
        # Проверяем, что кэш был инвалидирован
        cache_key = f"get_user_sessions:{mock_user_session.user_id}"
        mock_delete.assert_called_once_with(cache_key)
        
        # Проверяем, что метод вернул True
        assert result is True
        
        # Проверяем, что сессия была деактивирована
        assert mock_user_session.is_active is False
        assert mock_user_session.revoked_reason == "Test revoke by JTI"
        assert mock_user_session.revoked_at is not None

@pytest.mark.asyncio
async def test_revoke_session_by_jti_not_found(mock_session):
    """Тест отзыва сессии по JTI, которая не найдена."""
    # Настраиваем mock_session для имитации отсутствия сессии
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_first = MagicMock(return_value=None)
    mock_scalars.scalars.return_value.first = mock_first
    
    # Вызываем тестируемый метод
    result = await session_service.revoke_session_by_jti(
        session=mock_session,
        jti="non-existent-jti"
    )
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что коммит не был вызван
    mock_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_revoke_session_by_jti_error(mock_session, mock_user_session):
    """Тест отзыва сессии по JTI при возникновении ошибки."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_first = MagicMock(return_value=mock_user_session)
    mock_scalars.scalars.return_value.first = mock_first
    
    # Мокаем SQLAlchemyError для имитации ошибки при коммите
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await session_service.revoke_session_by_jti(
        session=mock_session,
        jti=mock_user_session.jti
    )
    
    # Проверяем, что метод вернул False при ошибке
    assert result is False

# Тесты для revoke_all_user_sessions
@pytest.mark.asyncio
async def test_revoke_all_user_sessions_success(mock_session, mock_user, mock_user_session):
    """Тест успешного отзыва всех сессий пользователя."""
    # Мокаем метод delete кэш-сервиса
    with patch('app.services.auth.cache_service.cache_service.delete', new_callable=AsyncMock) as mock_delete:
        # Настраиваем mock_session для имитации успешного запроса
        mock_execute = AsyncMock()
        mock_session.execute = mock_execute
        mock_scalars = MagicMock()
        mock_execute.return_value = mock_scalars
        mock_all = MagicMock(return_value=[mock_user_session])
        mock_scalars.scalars.return_value.all = mock_all
        
        # Вызываем тестируемый метод
        result = await session_service.revoke_all_user_sessions(
            session=mock_session,
            user_id=mock_user.id,
            exclude_jti="exclude-jti",
            reason="Test revoke all"
        )
        
        # Проверяем, что был вызван метод execute
        mock_session.execute.assert_called_once()
        
        # Проверяем, что был сделан коммит
        mock_session.commit.assert_called_once()
        
        # Проверяем, что кэш был инвалидирован
        cache_key = f"get_user_sessions:{mock_user.id}"
        mock_delete.assert_called_once_with(cache_key)
        
        # Проверяем, что метод вернул правильное количество отозванных сессий
        assert result == 1
        
        # Проверяем, что сессия была деактивирована
        assert mock_user_session.is_active is False
        assert mock_user_session.revoked_reason == "Test revoke all"
        assert mock_user_session.revoked_at is not None

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_no_sessions(mock_session, mock_user):
    """Тест отзыва всех сессий пользователя, когда сессий нет."""
    # Настраиваем mock_session для имитации отсутствия сессий
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_all = MagicMock(return_value=[])
    mock_scalars.scalars.return_value.all = mock_all
    
    # Вызываем тестируемый метод
    result = await session_service.revoke_all_user_sessions(
        session=mock_session,
        user_id=mock_user.id
    )
    
    # Проверяем, что метод вернул 0
    assert result == 0
    
    # Проверяем, что коммит не был вызван
    mock_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_error(mock_session, mock_user, mock_user_session):
    """Тест отзыва всех сессий пользователя при возникновении ошибки."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_all = MagicMock(return_value=[mock_user_session])
    mock_scalars.scalars.return_value.all = mock_all
    
    # Мокаем SQLAlchemyError для имитации ошибки при коммите
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await session_service.revoke_all_user_sessions(
        session=mock_session,
        user_id=mock_user.id
    )
    
    # Проверяем, что метод вернул 0 при ошибке
    assert result == 0

# Тесты для cleanup_expired_sessions
@pytest.mark.asyncio
async def test_cleanup_expired_sessions_success(mock_session, mock_user_session):
    """Тест успешной очистки просроченных сессий."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_all = MagicMock(return_value=[mock_user_session])
    mock_scalars.scalars.return_value.all = mock_all
    
    # Вызываем тестируемый метод
    result = await session_service.cleanup_expired_sessions(
        session=mock_session
    )
    
    # Проверяем, что был вызван метод execute
    mock_session.execute.assert_called_once()
    
    # Проверяем, что был сделан коммит
    mock_session.commit.assert_called_once()
    
    # Проверяем, что метод вернул правильное количество очищенных сессий
    assert result == 1
    
    # Проверяем, что сессия была деактивирована
    assert mock_user_session.is_active is False
    assert mock_user_session.revoked_reason == "Token expired"
    assert mock_user_session.revoked_at is not None

@pytest.mark.asyncio
async def test_cleanup_expired_sessions_no_sessions(mock_session):
    """Тест очистки просроченных сессий, когда просроченных сессий нет."""
    # Настраиваем mock_session для имитации отсутствия просроченных сессий
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_all = MagicMock(return_value=[])
    mock_scalars.scalars.return_value.all = mock_all
    
    # Вызываем тестируемый метод
    result = await session_service.cleanup_expired_sessions(
        session=mock_session
    )
    
    # Проверяем, что метод вернул 0
    assert result == 0
    
    # Проверяем, что коммит не был вызван
    mock_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_cleanup_expired_sessions_error(mock_session, mock_user_session):
    """Тест очистки просроченных сессий при возникновении ошибки."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_all = MagicMock(return_value=[mock_user_session])
    mock_scalars.scalars.return_value.all = mock_all
    
    # Мокаем SQLAlchemyError для имитации ошибки при коммите
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await session_service.cleanup_expired_sessions(
        session=mock_session
    )
    
    # Проверяем, что метод вернул 0 при ошибке
    assert result == 0

# Тесты для is_session_active
@pytest.mark.asyncio
async def test_is_session_active_true(mock_session, mock_user_session):
    """Тест проверки активности сессии, когда сессия активна."""
    # Настраиваем mock_session для имитации успешного запроса
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_first = MagicMock(return_value=mock_user_session)
    mock_scalars.scalars.return_value.first = mock_first
    
    # Вызываем тестируемый метод
    result = await session_service.is_session_active(
        session=mock_session,
        jti=mock_user_session.jti
    )
    
    # Проверяем, что метод вернул True
    assert result is True

@pytest.mark.asyncio
async def test_is_session_active_false_not_found(mock_session):
    """Тест проверки активности сессии, когда сессия не найдена."""
    # Настраиваем mock_session для имитации отсутствия сессии
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_scalars = MagicMock()
    mock_execute.return_value = mock_scalars
    mock_first = MagicMock(return_value=None)
    mock_scalars.scalars.return_value.first = mock_first
    
    # Вызываем тестируемый метод
    result = await session_service.is_session_active(
        session=mock_session,
        jti="non-existent-jti"
    )
    
    # Проверяем, что метод вернул False
    assert result is False

@pytest.mark.asyncio
async def test_is_session_active_error(mock_session):
    """Тест проверки активности сессии при возникновении ошибки."""
    # Мокаем SQLAlchemyError для имитации ошибки
    mock_session.execute.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await session_service.is_session_active(
        session=mock_session,
        jti="test-jti"
    )
    
    # Проверяем, что метод вернул False при ошибке
    assert result is False 