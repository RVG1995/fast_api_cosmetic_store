import pytest
from unittest.mock import MagicMock
from datetime import datetime
import sys
from types import SimpleNamespace

import asyncio

# Импортируем функцию для теста
from routers.carts import enrich_cart_with_product_data

@pytest.mark.asyncio
async def test_enrich_cart_none():
    result = await enrich_cart_with_product_data(None)
    assert result.id == 0
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
async def test_enrich_cart_items_none(monkeypatch):
    cart = MagicMock()
    cart.id = 1
    cart.user_id = 42
    cart.session_id = None
    cart.created_at = datetime.now()
    cart.updated_at = datetime.now()
    cart.items = None
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            return {}
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 1
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
async def test_enrich_cart_key_error(monkeypatch):
    cart = MagicMock()
    cart.id = 2
    cart.user_id = 42
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
            # Нет поля 'stock' — вызовет KeyError
            return {101: {"id": 101, "name": "Test", "price": 100.0}}
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 2
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
async def test_enrich_cart_attribute_error(monkeypatch):
    cart = MagicMock()
    cart.id = 3
    cart.user_id = 42
    cart.session_id = None
    # Не устанавливаем created_at/updated_at, вызовет AttributeError
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
    assert result.id == 3
    assert result.items[0].product_id == 101
    assert result.total_items == 2
    assert result.total_price == 200.0

@pytest.mark.asyncio
async def test_enrich_cart_type_error(monkeypatch):
    cart = MagicMock()
    cart.id = 4
    cart.user_id = 42
    cart.session_id = None
    cart.created_at = datetime.now()
    cart.updated_at = datetime.now()
    # items не список, а строка
    cart.items = "notalist"
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            return {}
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 4
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
async def test_enrich_cart_critical_error(monkeypatch):
    cart = MagicMock()
    cart.id = 5
    cart.user_id = 42
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
            raise ValueError("Критическая ошибка API")
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 5
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
async def test_enrich_cart_value_error(monkeypatch):
    cart = MagicMock()
    cart.id = 6
    cart.user_id = 42
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
            return {101: {"id": 101, "name": "Test", "price": "not_a_number", "stock": 5}}
    monkeypatch.setattr("routers.carts.product_api", MockProductAPI())
    result = await enrich_cart_with_product_data(cart)
    assert result.id == 6
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0 