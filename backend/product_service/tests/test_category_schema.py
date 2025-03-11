import pytest
from pydantic import ValidationError
from product_service.schema import (
    CategoryAddSchema,
    CategorySchema,
    CategoryUpdateSchema
)

class TestCategorySchemas:
    """Тесты для проверки схем категорий"""
    
    def test_category_add_schema_valid(self):
        """Тест создания схемы категории с валидными данными"""
        category_data = {
            "name": "Электроника",
            "slug": "electronics"
        }
        
        # Создаем схему - не должно быть исключений
        category = CategoryAddSchema(**category_data)
        
        # Проверяем заполнение полей
        assert category.name == "Электроника"
        assert category.slug == "electronics"
    
    def test_category_add_schema_missing_fields(self):
        """Тест создания схемы категории с отсутствующими полями"""
        # Отсутствует поле name
        category_data = {
            "slug": "electronics"
        }
        
        # Проверяем, что будет выброшено исключение
        with pytest.raises(ValidationError) as exc_info:
            CategoryAddSchema(**category_data)
        
        # Проверяем сообщение об ошибке
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert "Field required" in errors[0]["msg"]
        
        # Отсутствует поле slug
        category_data = {
            "name": "Электроника"
        }
        
        # Проверяем, что будет выброшено исключение
        with pytest.raises(ValidationError) as exc_info:
            CategoryAddSchema(**category_data)
        
        # Проверяем сообщение об ошибке
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("slug",)
        assert "Field required" in errors[0]["msg"]
    
    def test_category_add_schema_invalid_types(self):
        """Тест создания схемы категории с неверными типами данных"""
        category_data = {
            "name": 12345,  # Должна быть строка
            "slug": "electronics"
        }
        
        # Проверяем, что будет выброшено исключение
        with pytest.raises(ValidationError) as exc_info:
            CategoryAddSchema(**category_data)
        
        # Проверяем сообщение об ошибке
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert "Input should be a valid string" in errors[0]["msg"]
        
        # Проверка второго неверного типа
        category_data = {
            "name": "Электроника",
            "slug": 12345  # Должна быть строка
        }
        
        # Проверяем, что будет выброшено исключение
        with pytest.raises(ValidationError) as exc_info:
            CategoryAddSchema(**category_data)
        
        # Проверяем сообщение об ошибке
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("slug",)
        assert "Input should be a valid string" in errors[0]["msg"]
    
    def test_category_schema_valid(self):
        """Тест полной схемы категории с валидными данными"""
        category_data = {
            "id": 1,
            "name": "Электроника",
            "slug": "electronics"
        }
        
        # Создаем схему - не должно быть исключений
        category = CategorySchema(**category_data)
        
        # Проверяем заполнение полей
        assert category.id == 1
        assert category.name == "Электроника"
        assert category.slug == "electronics"
    
    def test_category_schema_missing_id(self):
        """Тест полной схемы категории без ID"""
        category_data = {
            "name": "Электроника",
            "slug": "electronics"
        }
        
        # Проверяем, что будет выброшено исключение
        with pytest.raises(ValidationError) as exc_info:
            CategorySchema(**category_data)
        
        # Проверяем сообщение об ошибке
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("id",)
        assert "Field required" in errors[0]["msg"]
    
    def test_category_update_schema_valid(self):
        """Тест схемы обновления категории с валидными данными"""
        # Полное обновление
        update_data = {
            "name": "Новое название",
            "slug": "new-slug"
        }
        
        # Создаем схему - не должно быть исключений
        category_update = CategoryUpdateSchema(**update_data)
        
        # Проверяем заполнение полей
        assert category_update.name == "Новое название"
        assert category_update.slug == "new-slug"
        
        # Частичное обновление - только имя
        update_data = {
            "name": "Новое название"
        }
        
        category_update = CategoryUpdateSchema(**update_data)
        assert category_update.name == "Новое название"
        assert category_update.slug is None
        
        # Частичное обновление - только slug
        update_data = {
            "slug": "new-slug"
        }
        
        category_update = CategoryUpdateSchema(**update_data)
        assert category_update.name is None
        assert category_update.slug == "new-slug"
        
        # Пустое обновление - допустимо, но ничего не изменится
        update_data = {}
        
        category_update = CategoryUpdateSchema(**update_data)
        assert category_update.name is None
        assert category_update.slug is None
    
    def test_category_update_schema_invalid_types(self):
        """Тест схемы обновления категории с неверными типами данных"""
        update_data = {
            "name": 12345,  # Должна быть строка
            "slug": "new-slug"
        }
        
        # Проверяем, что будет выброшено исключение
        with pytest.raises(ValidationError) as exc_info:
            CategoryUpdateSchema(**update_data)
        
        # Проверяем сообщение об ошибке
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert "Input should be a valid string" in errors[0]["msg"] 