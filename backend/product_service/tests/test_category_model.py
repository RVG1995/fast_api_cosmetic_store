import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock

from product_service.models import CategoryModel, SubCategoryModel, ProductModel

class TestCategoryModel:
    """Тесты для модели категорий"""
    
    @pytest.mark.asyncio
    async def test_create_category(self, mock_session):
        """Тест создания категории в базе данных"""
        # Создаем новую категорию
        new_category = CategoryModel(
            name="Мебель",
            slug="furniture"
        )
        
        # Имитируем добавление id при сохранении в БД
        def add_mock(obj):
            obj.id = 1
            return None
        
        mock_session.add.side_effect = add_mock
        
        # Добавляем объект в сессию
        mock_session.add(new_category)
        await mock_session.commit()
        
        # Проверяем, что модель правильно создана
        assert new_category.id == 1
        assert new_category.name == "Мебель"
        assert new_category.slug == "furniture"
        
        # Проверяем вызов методов сессии
        mock_session.add.assert_called_once_with(new_category)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_category(self, mock_session):
        """Тест чтения категории из базы данных"""
        # Создаем тестовую категорию
        mock_category = CategoryModel(id=1, name="Электроника", slug="electronics")
        
        # Настраиваем моки для цепочки вызовов
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_category
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # Устанавливаем возвращаемое значение для execute
        mock_session.execute.return_value = mock_result
        
        # Выполняем запрос
        query = select(CategoryModel).filter(CategoryModel.id == 1)
        result = await mock_session.execute(query)
        category = result.scalars().first()
        
        # Проверяем результат
        assert category is not None
        assert category.id == 1
        assert category.name == "Электроника"
        assert category.slug == "electronics"
    
    @pytest.mark.asyncio
    async def test_update_category(self, mock_session):
        """Тест обновления категории в базе данных"""
        # Создаем тестовую категорию
        mock_category = CategoryModel(id=1, name="Старое название", slug="old-slug")
        
        # Настраиваем моки для цепочки вызовов
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_category
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # Устанавливаем возвращаемое значение для execute
        mock_session.execute.return_value = mock_result
        
        # Выполняем запрос для получения категории
        query = select(CategoryModel).filter(CategoryModel.id == 1)
        result = await mock_session.execute(query)
        category = result.scalars().first()
        
        # Обновляем категорию
        category.name = "Новое название"
        category.slug = "new-slug"
        await mock_session.commit()
        
        # Проверяем результат
        assert category.id == 1
        assert category.name == "Новое название"
        assert category.slug == "new-slug"
        
        # Проверяем вызов методов сессии
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_category(self, mock_session):
        """Тест удаления категории из базы данных"""
        # Создаем тестовую категорию
        mock_category = CategoryModel(id=1, name="Электроника", slug="electronics")
        
        # Настраиваем моки для цепочки вызовов
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_category
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # Устанавливаем возвращаемое значение для execute
        mock_session.execute.return_value = mock_result
        
        # Выполняем запрос для получения категории
        query = select(CategoryModel).filter(CategoryModel.id == 1)
        result = await mock_session.execute(query)
        category = result.scalars().first()
        
        # Удаляем категорию
        await mock_session.delete(category)
        await mock_session.commit()
        
        # Проверяем вызов методов сессии
        mock_session.delete.assert_called_once_with(category)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_category_relationship_subcategory(self, mock_session):
        """Тест связи между категорией и подкатегориями"""
        # Создаем тестовую категорию с подкатегориями
        mock_subcategories = [
            SubCategoryModel(id=1, name="Смартфоны", slug="smartphones", category_id=1),
            SubCategoryModel(id=2, name="Ноутбуки", slug="laptops", category_id=1)
        ]
        
        mock_category = CategoryModel(id=1, name="Электроника", slug="electronics")
        mock_category.subcategories = mock_subcategories
        
        # Настраиваем моки для цепочки вызовов
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_category
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # Устанавливаем возвращаемое значение для execute
        mock_session.execute.return_value = mock_result
        
        # Выполняем запрос
        query = select(CategoryModel).filter(CategoryModel.id == 1)
        result = await mock_session.execute(query)
        category = result.scalars().first()
        
        # Проверяем результат
        assert category is not None
        assert len(category.subcategories) == 2
        assert category.subcategories[0].name == "Смартфоны"
        assert category.subcategories[1].slug == "laptops"
    
    @pytest.mark.asyncio
    async def test_category_relationship_products(self, mock_session):
        """Тест связи между категорией и продуктами"""
        # Создаем тестовую категорию с продуктами
        mock_products = [
            ProductModel(
                id=1, 
                name="iPhone 13", 
                category_id=1,
                brand_id=1,
                country_id=1,
                price=1000,
                stock=10
            ),
            ProductModel(
                id=2, 
                name="Samsung Galaxy", 
                category_id=1,
                brand_id=2,
                country_id=2,
                price=800,
                stock=15
            )
        ]
        
        mock_category = CategoryModel(id=1, name="Электроника", slug="electronics")
        mock_category.products = mock_products
        
        # Настраиваем моки для цепочки вызовов
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_category
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # Устанавливаем возвращаемое значение для execute
        mock_session.execute.return_value = mock_result
        
        # Выполняем запрос
        query = select(CategoryModel).filter(CategoryModel.id == 1)
        result = await mock_session.execute(query)
        category = result.scalars().first()
        
        # Проверяем результат
        assert category is not None
        assert len(category.products) == 2
        assert category.products[0].name == "iPhone 13"
        assert category.products[1].price == 800 