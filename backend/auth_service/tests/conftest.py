"""Общие фикстуры для всех тестов аутентификации."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Добавляем пути импорта для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Фикстуры для тестирования
@pytest.fixture
def mock_session():
    """Мок для сессии базы данных"""
    mock_sess = AsyncMock()
    return mock_sess

@pytest.fixture
def mock_admin_user():
    """Мок для администратора"""
    admin = MagicMock()
    admin.id = 2
    admin.email = "admin@example.com"
    admin.is_admin = True
    admin.is_super_admin = False
    admin.is_active = True
    return admin

@pytest.fixture
def mock_super_admin_user():
    """Мок для суперадминистратора"""
    super_admin = MagicMock()
    super_admin.id = 3
    super_admin.email = "superadmin@example.com"
    super_admin.is_admin = True
    super_admin.is_super_admin = True
    super_admin.is_active = True
    return super_admin

@pytest.fixture
def mock_user():
    """Мок для обычного пользователя"""
    user = MagicMock()
    user.id = 1
    user.email = "user@example.com"
    user.is_admin = False
    user.is_super_admin = False
    user.is_active = False
    return user 