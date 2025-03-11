import pytest
from httpx import AsyncClient, ASGITransport
from product_service.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


@pytest.mark.asyncio
async def test_post_products():
    """Тест для проверки POST запроса к /products"""
    # Тестовые данные для multipart/form-data
    test_data = {
        'name': 'test_product',
        'category_id': '1',
        'country_id': '1',
        'brand_id': '1',
        'subcategory_id': '1',
        'price': '10',
        'description': 'TEST',
        'stock': '10'
    }
    
    # Патчим все обращения к базе данных
    with patch('product_service.main.get_session') as mock_get_session:
        # Настраиваем мок сессии
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.refresh = MagicMock()
        
        # Настраиваем генератор для мока
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        # Патчим SQLAlchemy
        with patch('sqlalchemy.ext.asyncio.AsyncSession.commit', new_callable=AsyncMock) as mock_commit:
            with patch('sqlalchemy.ext.asyncio.AsyncSession.flush', new_callable=AsyncMock) as mock_flush:
                # Выполняем запрос с использованием формы
                async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
                    # Используем files для multipart/form-data
                    response = await ac.post(
                        '/products', 
                        files={},  # Пустой файл для создания multipart/form-data
                        data=test_data  # Поля формы
                    )
                    
                    # Проверяем результат
                    assert response.status_code == 200
                    data = response.json()
                    assert data == {"ok": "New product was added"} 