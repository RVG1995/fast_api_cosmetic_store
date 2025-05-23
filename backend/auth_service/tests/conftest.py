"""Конфигурационный файл pytest с общими фикстурами для тестов."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

# Добавляем пути импорта для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Фикстуры для тестирования
@pytest.fixture
def mock_session():
    """Мок для сессии базы данных."""
    session = AsyncMock(spec=AsyncSession)
    # Настраиваем поведение по умолчанию
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
def mock_user():
    """Мок для обычного пользователя."""
    user = MagicMock()
    user.id = 1
    user.email = "user@example.com"
    user.first_name = "User"
    user.last_name = "Test"
    user.is_active = True
    user.is_admin = False
    user.is_super_admin = False
    user.hashed_password = "hashed_password_123"
    return user

@pytest.fixture
def mock_admin_user():
    """Мок для администратора."""
    admin = MagicMock()
    admin.id = 2
    admin.email = "admin@example.com"
    admin.first_name = "Admin"
    admin.last_name = "User"
    admin.is_active = True
    admin.is_admin = True
    admin.is_super_admin = False
    admin.hashed_password = "hashed_password_456"
    return admin

@pytest.fixture
def mock_super_admin_user():
    """Мок для суперадминистратора."""
    super_admin = MagicMock()
    super_admin.id = 3
    super_admin.email = "superadmin@example.com"
    super_admin.first_name = "Super"
    super_admin.last_name = "Admin"
    super_admin.is_active = True
    super_admin.is_admin = True
    super_admin.is_super_admin = True
    super_admin.hashed_password = "hashed_password_789"
    return super_admin

@pytest.fixture
def patched_app():
    """Создает патченное приложение FastAPI для тестирования без реальных зависимостей."""
    with patch('database.setup_database'), \
         patch('database.create_superadmin'), \
         patch('database.create_default_user'), \
         patch('database.engine'), \
         patch('app.services.cache_service.initialize'), \
         patch('app.services.bruteforce_protection.initialize'), \
         patch('app.services.cache_service.close'), \
         patch('app.services.bruteforce_protection.close'), \
         patch('database.get_session'):
        from main import app
        return app

@pytest.fixture
def test_client(patched_app):
    """Создает тестовый клиент для патченного приложения FastAPI."""
    return TestClient(patched_app)

# Настройка для работы с асинхронными тестами
def pytest_configure(config):
    """Конфигурация pytest."""
    # Регистрируем asyncio как плагин
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test") 