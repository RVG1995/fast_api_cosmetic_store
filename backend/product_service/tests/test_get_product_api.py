import pytest
from httpx import AsyncClient, ASGITransport
from product_service.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


@pytest.mark.asyncio
async def test_get_product_by_id():
    """Тест для проверки GET запроса к /products/{product_id}"""
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
    
    # Патчим все обращения к базе данных
    with patch('product_service.main.get_session') as mock_get_session:
        # Настраиваем мок сессии
        mock_session = AsyncMock()
        
        # Создаем класс для имитации scalars().first()
        class ScalarsMock:
            def first(self):
                return mock_product
        
        # Настраиваем мок execute для возврата scalars().first()
        execute_result = MagicMock()
        execute_result.scalars.return_value = ScalarsMock()
        
        # Создаем функцию для имитации асинхронного execute
        async def mock_execute(*args, **kwargs):
            return execute_result
        
        # Устанавливаем её как метод mock_session
        mock_session.execute = mock_execute
        
        # Настраиваем генератор для мока
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        # Патчим SQLAlchemy напрямую
        with patch('sqlalchemy.ext.asyncio.AsyncSession.commit', new_callable=AsyncMock) as mock_commit:
            with patch('sqlalchemy.ext.asyncio.AsyncSession.flush', new_callable=AsyncMock) as mock_flush:
                with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', side_effect=mock_execute) as mock_execute_patch:
                    # Выполняем запрос
                    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
                        response = await ac.get('/products/1')
                        assert response.status_code == 200
                        
                        data = response.json()
                        assert data is not None
                        assert data["id"] == 1
                        assert data["name"] == "Test Product" 