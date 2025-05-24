"""Функциональные тесты для функций роутера корзины."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os
from pathlib import Path

# Добавляем путь к директории cart_service
current_file = Path(__file__).resolve()
cart_service_dir = current_file.parents[2]  # Поднимаемся до директории cart_service
sys.path.append(str(cart_service_dir))

# Теперь импортируем carts напрямую
from routers.carts import enrich_cart_with_product_data, get_cart_with_items, CartModel


@pytest.mark.asyncio
async def test_enrich_cart_with_product_data_empty():
    """Тест обогащения данными пустой корзины."""
    cart = None
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 0
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0


@pytest.mark.asyncio
async def test_enrich_cart_with_product_data_with_items(monkeypatch):
    """Тест обогащения данными корзины с товарами."""
    cart = MagicMock()
    cart.id = 1
    cart.user_id = 42
    cart.session_id = "sess"
    cart.created_at = datetime.now()
    cart.updated_at = datetime.now()
    
    item = MagicMock()
    item.id = 1
    item.product_id = 101
    item.quantity = 2
    item.added_at = datetime.now()
    item.updated_at = datetime.now()
    cart.items = [item]
    
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            return {101: {"id": 101, "name": "Test", "price": 100.0, "stock": 5}}
    
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 1
    assert result.items[0].product_id == 101
    assert result.items[0].quantity == 2
    assert result.total_items == 2
    assert result.total_price == 200.0


@pytest.mark.asyncio
async def test_enrich_cart_with_product_data_no_product_info(monkeypatch):
    """Тест обогащения данными корзины без информации о продукте."""
    cart = MagicMock()
    cart.id = 2
    cart.user_id = 42
    cart.session_id = "sess"
    cart.created_at = datetime.now()
    cart.updated_at = datetime.now()
    
    item = MagicMock()
    item.id = 1
    item.product_id = 999
    item.quantity = 1
    item.added_at = datetime.now()
    item.updated_at = datetime.now()
    cart.items = [item]
    
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            return {}
    
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 2
    assert result.items[0].product_id == 999
    assert result.items[0].product is None
    assert result.total_items == 0
    assert result.total_price == 0


@pytest.mark.asyncio
async def test_get_cart_with_items_user_none():
    """Тест получения корзины для неавторизованного пользователя."""
    session = AsyncMock()
    result = await get_cart_with_items(session, None)
    assert result is None


@pytest.mark.asyncio
async def test_get_cart_with_items_user_with_id(monkeypatch):
    """Тест получения корзины для авторизованного пользователя."""
    session = AsyncMock()
    user = MagicMock()
    user.id = 42
    
    async def mock_get_user_cart(session, user_id):
        cart = MagicMock()
        cart.id = 1
        return cart
    
    monkeypatch.setattr(CartModel, "get_user_cart", mock_get_user_cart)
    
    result = await get_cart_with_items(session, user)
    assert result.id == 1


@pytest.mark.asyncio
async def test_enrich_cart_with_product_data_attribute_error(monkeypatch):
    """Тест обработки AttributeError в функции обогащения данных."""
    cart = MagicMock()
    cart.id = 3
    cart.user_id = 42
    cart.session_id = "sess"
    
    # Не устанавливаем created_at и updated_at, чтобы вызвать AttributeError
    # Эмулируем ситуацию, когда при обращении к этим атрибутам возникнет AttributeError
    type(cart).created_at = property(lambda x: (_ for _ in ()).throw(AttributeError("no attribute 'created_at'")))
    type(cart).updated_at = property(lambda x: (_ for _ in ()).throw(AttributeError("no attribute 'updated_at'")))
    
    item = MagicMock()
    item.id = 1
    item.product_id = 101
    item.quantity = 2
    item.added_at = datetime.now()
    item.updated_at = datetime.now()
    cart.items = [item]
    
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            return {101: {"id": 101, "name": "Test", "price": 100.0, "stock": 5}}
    
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    
    # Функция должна обработать AttributeError и создать новые datetime объекты
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 3
    assert result.user_id == 42
    assert result.items[0].product_id == 101
    assert result.total_items == 2
    assert result.total_price == 200.0


@pytest.mark.asyncio
async def test_enrich_cart_with_product_data_key_error(monkeypatch):
    """Тест обработки KeyError в функции обогащения данных."""
    cart = MagicMock()
    cart.id = 4
    cart.user_id = 42
    # Важно! Для корректной работы с Pydantic
    cart.session_id = None
    cart.created_at = datetime.now()
    cart.updated_at = datetime.now()
    
    item = MagicMock()
    item.id = 1
    item.product_id = 101
    item.quantity = 2
    item.added_at = datetime.now()
    item.updated_at = datetime.now()
    cart.items = [item]
    
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            # Возвращаем информацию о продукте с отсутствующим полем 'stock'
            return {101: {"id": 101, "name": "Test", "price": 100.0}}
    
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    
    # В оригинальном коде, если отсутствует поле 'stock', товар не добавится в items из-за KeyError
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 4
    assert result.user_id == 42
    # Должен быть пустой список из-за перехвата ошибки
    assert len(result.items) == 0
    assert result.total_items == 0
    assert result.total_price == 0


@pytest.mark.asyncio
async def test_enrich_cart_with_product_data_critical_error(monkeypatch):
    """Тест обработки критической ошибки в функции обогащения данных."""
    cart = MagicMock()
    cart.id = 5
    cart.user_id = 42
    # Важно! Для корректной работы с Pydantic
    cart.session_id = None
    
    # Вызываем критическую ошибку при любом обращении к product_api
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            raise ValueError("Критическая ошибка API")
    
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    
    # Функция должна обработать критическую ошибку и вернуть пустую корзину
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 5
    assert result.user_id == 42
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0