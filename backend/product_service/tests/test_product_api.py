import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import asyncio

from product_service.main import app, get_session
from product_service.models import ProductModel


class TestProductAPI:
    """Тесты для API продуктов"""

    @pytest.mark.asyncio
    async def test_get_products(self, override_get_session, test_session):
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

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, override_get_session, test_session):
        """Тест для проверки GET запроса к /products/{product_id}"""
        # Создаем тестовый продукт
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
        test_session.add(test_product)
        await test_session.commit()

        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/products/1")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "Test Product"
            assert data["price"] == 100
            assert data["description"] == "Test Description"
            assert data["stock"] == 10
            assert data["image"] is None

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, override_get_session):
        """Тест для проверки GET запроса к /products/{product_id} с несуществующим ID"""    
        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/products/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            error = response.json()
            assert error["detail"] == "Product not found"
    
    @pytest.mark.asyncio
    async def test_create_product(self, override_get_session):
        """Тест для проверки POST запроса к /products"""
        # Подготавливаем данные для создания в формате Form
        product_data = {
            "name": "Test Product",
            "category_id": "1",
            "country_id": "1",
            "brand_id": "1",
            "subcategory_id": "1",
            "price": "100",
            "description": "Test Description",
            "stock": "10"
        }

        # Выполняем запрос с помощью AsyncClient, используя data вместо json
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/products", data=product_data)
            
            # Проверяем, что запрос успешен и возвращается ожидаемый формат ответа
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data == {"ok": "New product was added"}

    @pytest.mark.asyncio
    async def test_update_product(self, override_get_session, test_session):
        """Тест для проверки PUT запроса к /products/{product_id}"""
        # Создаем тестовый продукт
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
        )
        test_session.add(test_product)
        await test_session.commit()

        # Подготавливаем данные для обновления  
        update_data = {
            "name": "Updated Product",
            "price": 150,
            "description": "Updated Description",
            "stock": 15,
            "image": None
        }

        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put("/products/1", json=update_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "Updated Product"
            assert data["price"] == 150
            assert data["description"] == "Updated Description"
            assert data["stock"] == 15
            assert data["image"] is None

    @pytest.mark.asyncio
    async def test_delete_product(self, override_get_session):
        """Тест для проверки DELETE запроса к /products/{product_id}"""
        # Создаем тестовый продукт для базы данных
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
        )
        
        # Создаем патч для подключения к базе данных, чтобы возвращать тестовый объект
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute") as mock_execute:
            # Настраиваем возврат объекта
            mock_scalar = MagicMock()
            mock_scalar.first.return_value = test_product
            
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalar
            
            # Настраиваем execute для возврата мок-результата
            mock_execute.return_value = mock_result
            
            # Патчим метод delete сессии (используем AsyncMock для await)
            with patch("sqlalchemy.ext.asyncio.AsyncSession.delete", AsyncMock()) as mock_delete:
                # Патчим метод commit сессии (async)
                with patch("sqlalchemy.ext.asyncio.AsyncSession.commit", AsyncMock()) as mock_commit:
                    # Используем AsyncClient для выполнения запроса
                    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                        response = await client.delete("/products/1")
                        
                        # Проверяем статус ответа
                        assert response.status_code == status.HTTP_204_NO_CONTENT
                        
                        # Проверяем, что методы были вызваны
                        mock_delete.assert_called_once()
                        mock_commit.assert_called_once()