"""Конфигурационный файл pytest с общими фикстурами для тестов cart_service."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from datetime import datetime

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
def mock_admin_user():
    """Мок для администратора."""
    admin = MagicMock()
    admin.id = 1
    admin.email = "admin@example.com"
    admin.first_name = "Admin"
    admin.last_name = "User"
    admin.is_active = True
    admin.is_admin = True
    return admin

@pytest.fixture
def mock_cart_model():
    """Мок для модели корзины."""
    from models import CartModel
    
    # Создаем базовый мок для CartModel
    cart_model = MagicMock(spec=CartModel)
    # Добавляем нужные атрибуты и методы
    cart_model.id = 1
    cart_model.user_id = 1
    cart_model.session_id = "test-session-id"
    cart_model.created_at = datetime.now()
    cart_model.updated_at = datetime.now()
    cart_model.items = []
    
    # Настраиваем статические методы
    CartModel.get_by_id = AsyncMock()
    CartModel.get_user_carts = AsyncMock()
    
    return cart_model

@pytest.fixture
def mock_cart_items():
    """Мок для элементов корзины."""
    # Создаем несколько элементов корзины
    item1 = MagicMock()
    item1.id = 1
    item1.cart_id = 1
    item1.product_id = 101
    item1.quantity = 2
    item1.added_at = datetime.now()
    item1.updated_at = datetime.now()
    
    item2 = MagicMock()
    item2.id = 2
    item2.cart_id = 1
    item2.product_id = 102
    item2.quantity = 1
    item2.added_at = datetime.now()
    item2.updated_at = datetime.now()
    
    return [item1, item2]

@pytest.fixture
def mock_product_api():
    """Мок для API продуктов."""
    from product_api import ProductAPI
    
    # Создаем мок для ProductAPI
    product_api = MagicMock(spec=ProductAPI)
    product_api.get_products_info = AsyncMock(return_value={
        101: {"id": 101, "name": "Test Product 1", "price": 100.0},
        102: {"id": 102, "name": "Test Product 2", "price": 200.0}
    })
    
    return product_api

@pytest.fixture
def mock_cache():
    """Мок для кеша."""
    # Создаем мок для функций кеширования
    cache_get = AsyncMock(return_value=None)  # По умолчанию кеш пуст
    cache_set = AsyncMock()
    
    return {
        "cache_get": cache_get,
        "cache_set": cache_set
    }

@pytest.fixture
def mock_user_info():
    """Мок для информации о пользователе."""
    user_info = AsyncMock(return_value={
        "id": 1,
        "email": "user@example.com",
        "first_name": "Test",
        "last_name": "User"
    })
    
    return user_info

@pytest.fixture
def patched_app():
    """Создает патченное приложение FastAPI для тестирования без реальных зависимостей."""
    with patch('database.get_session'), \
         patch('auth.get_current_admin_user'), \
         patch('product_api.ProductAPI'), \
         patch('cache.cache_get'), \
         patch('cache.cache_set'), \
         patch('auth.get_user_info'):
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