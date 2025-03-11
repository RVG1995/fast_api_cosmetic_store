import pytest
from httpx import AsyncClient, ASGITransport
from product_service.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


@pytest.mark.asyncio
async def test_post_product_schema_validation():
    """Тест валидации схемы продукта при POST запросе"""
    # Некорректные данные: отсутствует обязательное поле stock
    invalid_product_data = {
        'name': 'test_product',
        'category_id': '1',
        'country_id': '1',
        'brand_id': '1',
        'subcategory_id': '1',
        'price': '10',
        'description': 'TEST',
        # поле stock отсутствует
    }
    
    # Патчим все обращения к базе данных
    with patch('product_service.main.get_session') as mock_get_session:
        # Настраиваем мок сессии
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        
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
                        data=invalid_product_data  # Некорректные данные
                    )
                    
                    # Проверяем что запрос неудачный из-за отсутствия поля stock
                    assert response.status_code == 422  # Unprocessable Entity
                    
                    # Проверяем содержимое ошибки
                    error = response.json()
                    assert "detail" in error
                    
                    # Находим ошибку о пропущенном поле stock
                    field_errors = [err for err in error["detail"] if err.get("loc") and "stock" in err.get("loc")]
                    assert len(field_errors) > 0


@pytest.mark.asyncio
async def test_post_product_invalid_type():
    """Тест валидации типов данных в схеме при POST запросе"""
    # Некорректные данные: неверный тип price (должен быть число, передаем строку)
    invalid_product_data = {
        'name': 'test_product',
        'category_id': '1',
        'country_id': '1',
        'brand_id': '1',
        'subcategory_id': '1',
        'price': 'not-a-number',  # Неверный тип данных
        'description': 'TEST',
        'stock': '10'
    }
    
    # Патчим все обращения к базе данных
    with patch('product_service.main.get_session') as mock_get_session:
        # Настраиваем мок сессии
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        
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
                        data=invalid_product_data  # Некорректные данные
                    )
                    
                    # Проверяем что запрос неудачный из-за неверного типа данных price
                    assert response.status_code == 422  # Unprocessable Entity
                    
                    # Проверяем содержимое ошибки
                    error = response.json()
                    assert "detail" in error
                    
                    # Находим ошибку о неверном типе поля price
                    price_errors = [err for err in error["detail"] if err.get("loc") and "price" in err.get("loc")]
                    assert len(price_errors) > 0


@pytest.mark.asyncio
async def test_put_product_schema_validation():
    """Тест валидации схемы обновления продукта при PUT запросе"""
    # В схеме обновления все поля опциональные, отправляем только price
    update_data = {
        'price': 'not-a-number',  # Неверный тип данных
    }
    
    # Патчим все обращения к базе данных
    with patch('product_service.main.get_session') as mock_get_session:
        # Настраиваем мок сессии
        mock_session = AsyncMock()
        
        # Создаем класс для имитации scalars().first()
        mock_product = MagicMock()
        mock_product.id = 1
        
        class ScalarsMock:
            def first(self):
                return mock_product
        
        # Создаем мок для результата выполнения execute
        execute_result = MagicMock()
        execute_result.scalars.return_value = ScalarsMock()
        
        # Создаем асинхронную функцию для мокирования execute
        async def mock_execute(*args, **kwargs):
            return execute_result
        
        # Устанавливаем моки
        mock_session.execute = mock_execute
        mock_session.commit = AsyncMock()
        
        # Настраиваем генератор для мока
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        # Патчим SQLAlchemy
        with patch('sqlalchemy.ext.asyncio.AsyncSession.commit', new_callable=AsyncMock) as mock_commit:
            with patch('sqlalchemy.ext.asyncio.AsyncSession.execute', side_effect=mock_execute) as mock_execute_patch:
                # Выполняем запрос обновления продукта
                async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
                    response = await ac.put(
                        '/products/1', 
                        json=update_data
                    )
                    
                    # Проверяем что запрос неудачный из-за неверного типа данных price
                    assert response.status_code == 422  # Unprocessable Entity
                    
                    # Проверяем содержимое ошибки
                    error = response.json()
                    assert "detail" in error
                    
                    # Находим ошибку о неверном типе поля price
                    price_errors = [err for err in error["detail"] if err.get("loc") and "price" in err.get("loc")]
                    assert len(price_errors) > 0 