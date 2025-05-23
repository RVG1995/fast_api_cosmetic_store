"""Тесты для модуля database."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os
import contextlib
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.exc import SQLAlchemyError

# Добавляем пути импорта для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import database
from models import UserModel


@pytest.mark.asyncio
async def test_get_session():
    """Тест получения сессии базы данных."""
    # Создаем фиктивный генератор сессий
    mock_session = AsyncMock()
    
    # Патчим new_session в database
    with patch('database.new_session') as mock_new_session:
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Получаем сессию из функции get_session
        session_generator = database.get_session()
        session = await session_generator.__anext__()
        
        # Проверяем, что session - это наш мок
        assert session == mock_session


@pytest.mark.asyncio
async def test_create_superadmin_success():
    """Тест успешного создания суперадминистратора."""
    # Мокаем настройки
    mock_settings = MagicMock()
    mock_settings.SUPERADMIN_EMAIL = "admin@example.com"
    mock_settings.SUPERADMIN_PASSWORD = "password123"
    mock_settings.SUPERADMIN_FIRST_NAME = "Admin"
    mock_settings.SUPERADMIN_LAST_NAME = "User"
    
    # Мокаем сессию и методы UserModel
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    
    # Патч для класса UserModel
    get_by_email_mock = AsyncMock(return_value=None)  # Пользователь не существует
    
    # Патч для get_password_hash
    hashed_password_mock = AsyncMock(return_value="hashed_password_123")
    
    with patch('database.settings', mock_settings), \
         patch('database.new_session') as mock_new_session, \
         patch('models.UserModel.get_by_email', get_by_email_mock), \
         patch('database.get_password_hash', hashed_password_mock), \
         patch('database.logger'):
        
        # Настраиваем мок new_session для контекстного менеджера
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Вызываем тестируемую функцию
        await database.create_superadmin()
        
        # Проверяем, что get_by_email был вызван с правильными аргументами
        get_by_email_mock.assert_called_once_with(mock_session, "admin@example.com")
        
        # Проверяем, что get_password_hash был вызван с правильными аргументами
        hashed_password_mock.assert_called_once_with("password123")
        
        # Проверяем, что add и commit были вызваны
        assert mock_session.add.called
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_superadmin_already_exists():
    """Тест, когда суперадминистратор уже существует."""
    # Мокаем настройки
    mock_settings = MagicMock()
    mock_settings.SUPERADMIN_EMAIL = "admin@example.com"
    mock_settings.SUPERADMIN_PASSWORD = "password123"
    
    # Создаем мок существующего суперадмина
    existing_admin = MagicMock()
    existing_admin.is_super_admin = True
    
    # Мокаем сессию
    mock_session = AsyncMock()
    
    # Патч для класса UserModel
    get_by_email_mock = AsyncMock(return_value=existing_admin)  # Пользователь существует
    
    with patch('database.settings', mock_settings), \
         patch('database.new_session') as mock_new_session, \
         patch('models.UserModel.get_by_email', get_by_email_mock), \
         patch('database.logger'):
        
        # Настраиваем мок new_session для контекстного менеджера
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Вызываем тестируемую функцию
        await database.create_superadmin()
        
        # Проверяем, что get_by_email был вызван с правильными аргументами
        get_by_email_mock.assert_called_once_with(mock_session, "admin@example.com")
        
        # Проверяем, что сессия commit не вызывалась, т.к. пользователь уже существует
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_superadmin_no_env_variables():
    """Тест, когда не указаны переменные окружения для суперадминистратора."""
    # Мокаем настройки с пустыми данными
    mock_settings = MagicMock()
    mock_settings.SUPERADMIN_EMAIL = ""
    mock_settings.SUPERADMIN_PASSWORD = ""
    
    with patch('database.settings', mock_settings), \
         patch('database.logger') as mock_logger:
        
        # Вызываем тестируемую функцию
        await database.create_superadmin()
        
        # Проверяем, что было залогировано предупреждение
        mock_logger.warning.assert_called_once_with(
            "SUPERADMIN_EMAIL или SUPERADMIN_PASSWORD не указаны в .env файле"
        )


@pytest.mark.asyncio
async def test_create_superadmin_sqlalchemy_error():
    """Тест обработки ошибки SQLAlchemy при создании суперадминистратора."""
    # Мокаем настройки
    mock_settings = MagicMock()
    mock_settings.SUPERADMIN_EMAIL = "admin@example.com"
    mock_settings.SUPERADMIN_PASSWORD = "password123"
    mock_settings.SUPERADMIN_FIRST_NAME = "Admin"
    mock_settings.SUPERADMIN_LAST_NAME = "User"
    
    # Мокаем сессию и методы UserModel
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
    
    # Патч для класса UserModel
    get_by_email_mock = AsyncMock(return_value=None)  # Пользователь не существует
    
    # Патч для get_password_hash
    hashed_password_mock = AsyncMock(return_value="hashed_password_123")
    
    with patch('database.settings', mock_settings), \
         patch('database.new_session') as mock_new_session, \
         patch('models.UserModel.get_by_email', get_by_email_mock), \
         patch('database.get_password_hash', hashed_password_mock), \
         patch('database.logger') as mock_logger:
        
        # Настраиваем мок new_session для контекстного менеджера
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Вызываем тестируемую функцию
        await database.create_superadmin()
        
        # Проверяем, что было залогировано сообщение об ошибке
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_create_default_user_success():
    """Тест успешного создания обычного пользователя."""
    # Мокаем настройки
    mock_settings = MagicMock()
    mock_settings.DEFAULT_USER_EMAIL = "user@example.com"
    mock_settings.DEFAULT_USER_PASSWORD = "password123"
    mock_settings.DEFAULT_USER_FIRST_NAME = "Test"
    mock_settings.DEFAULT_USER_LAST_NAME = "User"
    
    # Мокаем сессию и методы UserModel
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    
    # Патч для класса UserModel
    get_by_email_mock = AsyncMock(return_value=None)  # Пользователь не существует
    
    # Патч для get_password_hash
    hashed_password_mock = AsyncMock(return_value="hashed_password_123")
    
    with patch('database.settings', mock_settings), \
         patch('database.new_session') as mock_new_session, \
         patch('models.UserModel.get_by_email', get_by_email_mock), \
         patch('database.get_password_hash', hashed_password_mock), \
         patch('database.logger'):
        
        # Настраиваем мок new_session для контекстного менеджера
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Вызываем тестируемую функцию
        await database.create_default_user()
        
        # Проверяем, что get_by_email был вызван с правильными аргументами
        get_by_email_mock.assert_called_once_with(mock_session, "user@example.com")
        
        # Проверяем, что get_password_hash был вызван с правильными аргументами
        hashed_password_mock.assert_called_once_with("password123")
        
        # Проверяем, что add и commit были вызваны
        assert mock_session.add.called
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_default_user_already_exists():
    """Тест, когда обычный пользователь уже существует."""
    # Мокаем настройки
    mock_settings = MagicMock()
    mock_settings.DEFAULT_USER_EMAIL = "user@example.com"
    mock_settings.DEFAULT_USER_PASSWORD = "password123"
    
    # Создаем мок существующего пользователя
    existing_user = MagicMock()
    
    # Мокаем сессию
    mock_session = AsyncMock()
    
    # Патч для класса UserModel
    get_by_email_mock = AsyncMock(return_value=existing_user)  # Пользователь существует
    
    with patch('database.settings', mock_settings), \
         patch('database.new_session') as mock_new_session, \
         patch('models.UserModel.get_by_email', get_by_email_mock), \
         patch('database.logger'):
        
        # Настраиваем мок new_session для контекстного менеджера
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Вызываем тестируемую функцию
        await database.create_default_user()
        
        # Проверяем, что get_by_email был вызван с правильными аргументами
        get_by_email_mock.assert_called_once_with(mock_session, "user@example.com")
        
        # Проверяем, что сессия commit не вызывалась, т.к. пользователь уже существует
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_default_user_no_env_variables():
    """Тест, когда не указаны переменные окружения для обычного пользователя."""
    # Мокаем настройки с пустыми данными
    mock_settings = MagicMock()
    mock_settings.DEFAULT_USER_EMAIL = ""
    mock_settings.DEFAULT_USER_PASSWORD = ""
    
    with patch('database.settings', mock_settings), \
         patch('database.logger') as mock_logger:
        
        # Вызываем тестируемую функцию
        await database.create_default_user()
        
        # Проверяем, что было залогировано предупреждение
        mock_logger.warning.assert_called_once_with(
            "DEFAULT_USER_EMAIL или DEFAULT_USER_PASSWORD не указаны в .env файле"
        )


@pytest.mark.asyncio
async def test_create_default_user_sqlalchemy_error():
    """Тест обработки ошибки SQLAlchemy при создании обычного пользователя."""
    # Мокаем настройки
    mock_settings = MagicMock()
    mock_settings.DEFAULT_USER_EMAIL = "user@example.com"
    mock_settings.DEFAULT_USER_PASSWORD = "password123"
    mock_settings.DEFAULT_USER_FIRST_NAME = "Test"
    mock_settings.DEFAULT_USER_LAST_NAME = "User"
    
    # Мокаем сессию и методы UserModel
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
    
    # Патч для класса UserModel
    get_by_email_mock = AsyncMock(return_value=None)  # Пользователь не существует
    
    # Патч для get_password_hash
    hashed_password_mock = AsyncMock(return_value="hashed_password_123")
    
    with patch('database.settings', mock_settings), \
         patch('database.new_session') as mock_new_session, \
         patch('models.UserModel.get_by_email', get_by_email_mock), \
         patch('database.get_password_hash', hashed_password_mock), \
         patch('database.logger') as mock_logger:
        
        # Настраиваем мок new_session для контекстного менеджера
        mock_new_session.return_value = AsyncMock()
        mock_new_session.return_value.__aenter__.return_value = mock_session
        
        # Вызываем тестируемую функцию
        await database.create_default_user()
        
        # Проверяем, что было залогировано сообщение об ошибке
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_setup_database():
    """Тест настройки базы данных."""
    # Создаем мок для engine
    mock_engine = AsyncMock(spec=AsyncEngine)
    
    # Создаем мок для connection
    mock_conn = AsyncMock()
    
    # Создаем контекстный менеджер для engine.begin()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_engine.begin.return_value = mock_context
    
    # Мокаем Base.metadata
    mock_metadata = MagicMock()
    
    with patch('database.engine', mock_engine), \
         patch('database.Base.metadata', mock_metadata):
        
        # Вызываем тестируемую функцию
        await database.setup_database()
        
        # Проверяем, что engine.begin был вызван
        mock_engine.begin.assert_called_once()
        
        # Проверяем, что conn.run_sync был вызван дважды
        assert mock_conn.run_sync.call_count == 2
        
        # Проверяем, что drop_all и create_all были вызваны
        mock_conn.run_sync.assert_any_call(mock_metadata.drop_all)
        mock_conn.run_sync.assert_any_call(mock_metadata.create_all) 