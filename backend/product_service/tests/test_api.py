import pytest
from httpx import AsyncClient, ASGITransport
from product_service.main import app
from unittest.mock import MagicMock, AsyncMock, patch
from product_service.models import ProductModel
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio


@pytest.fixture
async def mock_db_session():
    """Создает мок для сессии базы данных"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Настраиваем мок для ответа на запрос get_products
    mock_product = {
        "id": 1,
        "name": "Test Product",
        "category_id": 1,
        "country_id": 1,
        "brand_id": 1,
        "subcategory_id": 1,
        "price": 100,
        "description": "Test Description",
        "stock": 10,
        "in_stock": True,
        "image": None
    }
    
    mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_product]
    mock_session.commit = AsyncMock()
    
    return mock_session


@pytest.mark.asyncio
async def test_get_products(mock_session):
    """Тест для проверки GET запроса к /products"""
    # Настраиваем мок для возвращаемых данных
    mock_product = MagicMock()
    mock_product.id = 1
    mock_product.name = "Test Product"
    mock_product.category_id = 1
    mock_product.country_id = 1
    mock_product.brand_id = 1
    mock_product.subcategory_id = 1
    mock_product.price = 100
    mock_product.description = "Test Description"
    mock_product.stock = 10
    mock_product.in_stock = True
    mock_product.image = None
    
    # Настраиваем возвращаемые значения для сессии
    mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_product]
    
    # Выполняем запрос
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        response = await ac.get('/products')
        assert response.status_code == 200
        
        data = response.json()
        assert data != []
        assert len(data) == 1
        