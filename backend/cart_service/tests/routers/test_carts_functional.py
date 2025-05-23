import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import asyncio

from routers import carts

@pytest.mark.asyncio
def test_enrich_cart_with_product_data_empty():
    cart = None
    result = asyncio.run(carts.enrich_cart_with_product_data(cart))
    assert result.id == 0
    assert result.items == []
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
def test_enrich_cart_with_product_data_with_items(monkeypatch):
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
    monkeypatch.setattr(carts, "product_api", MockProductAPI())
    result = asyncio.run(carts.enrich_cart_with_product_data(cart))
    assert result.id == 1
    assert result.items[0].product_id == 101
    assert result.items[0].quantity == 2
    assert result.total_items == 2
    assert result.total_price == 200.0

@pytest.mark.asyncio
def test_enrich_cart_with_product_data_no_product_info(monkeypatch):
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
    monkeypatch.setattr(carts, "product_api", MockProductAPI())
    result = asyncio.run(carts.enrich_cart_with_product_data(cart))
    assert result.id == 2
    assert result.items[0].product_id == 999
    assert result.items[0].product is None
    assert result.total_items == 0
    assert result.total_price == 0

@pytest.mark.asyncio
def test_get_cart_with_items_user_none(monkeypatch):
    session = AsyncMock()
    result = asyncio.run(carts.get_cart_with_items(session, None))
    assert result is None

@pytest.mark.asyncio
def test_get_cart_with_items_user_with_id(monkeypatch):
    session = AsyncMock()
    user = MagicMock()
    user.id = 42
    async def mock_get_user_cart(session, user_id):
        cart = MagicMock()
        cart.id = 1
        return cart
    monkeypatch.setattr(carts.CartModel, "get_user_cart", mock_get_user_cart)
    result = asyncio.run(carts.get_cart_with_items(session, user))
    assert result.id == 1 