import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from product_service.main import app
from product_service.models import CategoryModel

class TestCategoryAPI:
    """Тесты для API категорий"""

    @pytest.mark.asyncio
    async def test_get_categories(self, override_get_session, test_session):
        """Тест получения списка категорий"""
        # Создаем тестовые данные
        categories = [
            CategoryModel(id=1, name="Электроника", slug="electronics"),
            CategoryModel(id=2, name="Одежда", slug="clothes"),
            CategoryModel(id=3, name="Книги", slug="books")
        ]
        
        # Добавляем тестовые данные в сессию
        for category in categories:
            test_session.add(category)
        await test_session.commit()
        
        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/categories")
            
            # Проверяем результат
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 3
            assert data[0]["id"] == 1
            assert data[0]["name"] == "Электроника"
            assert data[1]["slug"] == "clothes"
            assert data[2]["id"] == 3
    
    @pytest.mark.asyncio
    async def test_get_category_by_id(self, override_get_session, test_session):
        """Тест получения категории по ID"""
        # Создаем тестовую категорию
        category = CategoryModel(id=1, name="Электроника", slug="electronics")
        test_session.add(category)
        await test_session.commit()
        
        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/categories/1")
            
            # Проверяем результат
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "Электроника"
            assert data["slug"] == "electronics"
    
    @pytest.mark.asyncio
    async def test_get_category_not_found(self, override_get_session):
        """Тест получения несуществующей категории"""
        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/categories/999")
            
            # Проверяем результат
            assert response.status_code == status.HTTP_404_NOT_FOUND
            error = response.json()
            assert error["detail"] == "Category not found"
    
    @pytest.mark.asyncio
    async def test_create_category(self, override_get_session):
        """Тест создания новой категории"""
        # Подготавливаем данные для создания
        category_data = {
            "name": "Электроника",
            "slug": "electronics"
        }
        
        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/categories", json=category_data)
            
            # Проверяем результат
            assert response.status_code == status.HTTP_200_OK
            created_category = response.json()
            assert created_category["id"] is not None
            assert created_category["name"] == "Электроника"
            assert created_category["slug"] == "electronics"
    
    @pytest.mark.asyncio
    async def test_update_category(self, override_get_session, test_session):
        """Тест обновления категории"""
        # Создаем тестовую категорию
        category = CategoryModel(id=1, name="Старое название", slug="old-slug")
        test_session.add(category)
        await test_session.commit()
        
        # Данные для обновления
        update_data = {
            "name": "Новое название",
            "slug": "new-slug"
        }
        
        # Выполняем запрос с помощью AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put("/categories/1", json=update_data)
            
            # Проверяем результат
            assert response.status_code == status.HTTP_200_OK
            updated_category = response.json()
            assert updated_category["id"] == 1
            assert updated_category["name"] == "Новое название"
            assert updated_category["slug"] == "new-slug"
            
            # Проверяем, что данные действительно обновились в БД
            await test_session.refresh(category)
            assert category.name == "Новое название"
            assert category.slug == "new-slug" 