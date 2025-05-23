import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
import importlib
from schema import UserCartSchema, PaginatedUserCartsResponse, UserCartItemSchema
from datetime import datetime

@pytest_asyncio.fixture
def app_with_mocked_admin(monkeypatch):
    class MockProductAPI:
        async def get_products_info(self, product_ids):
            return {101: {"id": 101, "name": "Product 1", "price": 100.0}}
    async def mock_user_info(user_id):
        return {"id": user_id, "first_name": "Test", "last_name": "User", "email": "user@example.com"}
    monkeypatch.setattr('routers.admin_carts.product_api', MockProductAPI())
    monkeypatch.setattr('routers.admin_carts.cache_get', AsyncMock(return_value=None))
    monkeypatch.setattr('routers.admin_carts.cache_set', AsyncMock())
    monkeypatch.setattr('routers.admin_carts.get_user_info', mock_user_info)
    monkeypatch.setattr('routers.admin_carts.get_session', lambda: AsyncMock())
    from routers.admin_carts import router, get_current_admin_user
    app = FastAPI()
    app.dependency_overrides[get_current_admin_user] = lambda: MagicMock(id=42)
    app.include_router(router)
    return app

@pytest_asyncio.fixture
async def httpx_client(app_with_mocked_admin):
    async with AsyncClient(transport=ASGITransport(app=app_with_mocked_admin), base_url="http://test") as ac:
        yield ac

def make_cart(idx=1):
    return {
        "id": idx,
        "user_id": 42,
        "user_name": "Test User",
        "user_email": "user@example.com",
        "session_id": f"session-{idx}",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "items": [
            {
                "id": 1,
                "product_id": 101,
                "quantity": 2,
                "added_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "product_name": "Product 1",
                "product_price": 100.0
            }
        ],
        "total_items": 2,
        "items_count": 1,
        "total_price": 200.0
    }

@pytest.mark.asyncio
async def test_admin_carts_success(httpx_client, monkeypatch):
    # Мокаем CartModel.get_user_carts
    async def mock_get_user_carts(session, page, limit, sort_by, sort_order, user_id=None, filter=None, search=None):
        cart = MagicMock()
        cart.id = 1
        cart.user_id = 42
        cart.session_id = "session-1"
        cart.created_at = datetime.now()
        cart.updated_at = datetime.now()
        item = MagicMock()
        item.id = 1
        item.product_id = 101
        item.quantity = 2
        item.added_at = datetime.now()
        item.updated_at = datetime.now()
        cart.items = [item]
        return [cart], 1
    monkeypatch.setattr('models.CartModel.get_user_carts', mock_get_user_carts)
    resp = await httpx_client.get("/admin/carts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["user_name"] == "Test User"
    assert data["items"][0]["total_price"] == 200.0

@pytest.mark.asyncio
async def test_admin_cart_by_id_success(httpx_client, monkeypatch):
    # Мокаем CartModel.get_by_id
    async def mock_get_by_id(session, cart_id):
        cart = MagicMock()
        cart.id = cart_id
        cart.user_id = 42
        cart.session_id = "session-1"
        cart.created_at = datetime.now()
        cart.updated_at = datetime.now()
        item = MagicMock()
        item.id = 1
        item.product_id = 101
        item.quantity = 2
        item.added_at = datetime.now()
        item.updated_at = datetime.now()
        cart.items = [item]
        return cart
    monkeypatch.setattr('models.CartModel.get_by_id', mock_get_by_id)
    resp = await httpx_client.get("/admin/carts/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["user_name"] == "Test User"
    assert data["total_price"] == 200.0

@pytest.mark.asyncio
async def test_admin_cart_by_id_not_found(httpx_client, monkeypatch):
    async def mock_get_by_id(session, cart_id):
        return None
    monkeypatch.setattr('models.CartModel.get_by_id', mock_get_by_id)
    resp = await httpx_client.get("/admin/carts/999")
    assert resp.status_code == 404
    assert "Корзина не найдена" in resp.text

@pytest.mark.asyncio
async def test_admin_carts_empty(httpx_client, monkeypatch):
    async def mock_get_user_carts(session, page, limit, sort_by, sort_order, user_id=None, filter=None, search=None):
        return [], 0
    monkeypatch.setattr('models.CartModel.get_user_carts', mock_get_user_carts)
    resp = await httpx_client.get("/admin/carts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []

@pytest.mark.asyncio
async def test_admin_carts_internal_error(httpx_client, monkeypatch):
    async def mock_get_user_carts(*a, **kw):
        raise Exception("fail")
    monkeypatch.setattr('models.CartModel.get_user_carts', mock_get_user_carts)
    try:
        resp = await httpx_client.get("/admin/carts")
        assert resp.status_code == 200  # роутер должен вернуть пустой список, а не пробросить ошибку
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
    except Exception as e:
        pytest.fail(f"Exception проброшен наружу: {e}")

@pytest.mark.asyncio
async def test_admin_cart_by_id_internal_error(httpx_client, monkeypatch):
    async def mock_get_by_id(*a, **kw):
        raise Exception("fail")
    monkeypatch.setattr('models.CartModel.get_by_id', mock_get_by_id)
    resp = await httpx_client.get("/admin/carts/1")
    assert resp.status_code == 500
    assert "Ошибка сервера" in resp.text 