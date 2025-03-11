import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from product_service.main import app
from product_service.models import ProductModel

# Асинхронный тест с использованием фикстуры override_get_session
@pytest.mark.asyncio
async def test_get_products(override_get_session, test_session):
    """Тест для проверки GET запроса к /products"""
    # Создаем тестовые данные
    test_product = ProductModel(
        id=1,
        name="Test Product",
        category_id=1,
        country_id=1,
        brand_id=1,
        subcategory_id=1,
        price=100,
        description="Test Description",
        stock=10,
        image=None
        # in_stock генерируется автоматически на основе stock
    )
    
    # Добавляем тестовые данные в сессию
    test_session.add(test_product)
    await test_session.commit()
    
    # Выполняем запрос с помощью AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products")
        
        # Проверяем результат
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data != []
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Test Product"
        assert data[0]["price"] == 100 