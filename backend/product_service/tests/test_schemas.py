import pytest
from pydantic import ValidationError
from product_service.schema import (
    ProductAddSchema, 
    ProductSchema, 
    ProductUpdateSchema,
    CategoryAddSchema,
    CategorySchema
)

class TestProductSchemas:
    """Тесты для схем продуктов"""
    
    def test_product_add_schema_valid(self):
        """Тест создания продукта с валидными данными"""
        product_data = {
            "name": "Test Product",
            "category_id": 1,
            "country_id": 1,
            "brand_id": 1,
            "price": 100,
            "stock": 10,
        }
        
        # Создаем схему - не должно быть исключений
        product = ProductAddSchema(**product_data)
        
        # Проверяем заполнение полей
        assert product.name == "Test Product"
        assert product.category_id == 1
        assert product.country_id == 1
        assert product.brand_id == 1
        assert product.price == 100
        assert product.stock == 10
        
        # Проверяем опциональные поля
        assert product.subcategory_id is None
        assert product.description is None
        assert product.image is None
    
    def test_product_add_schema_with_optional_fields(self):
        """Тест создания продукта со всеми полями"""
        product_data = {
            "name": "Test Product",
            "category_id": 1,
            "country_id": 1,
            "brand_id": 1,
            "subcategory_id": 2,
            "price": 100,
            "description": "Test Description",
            "stock": 10,
            "image": "test.jpg"
        }
        
        product = ProductAddSchema(**product_data)
        
        # Проверяем опциональные поля
        assert product.subcategory_id == 2
        assert product.description == "Test Description"
        assert product.image == "test.jpg"
    
    def test_product_add_schema_missing_required_fields(self):
        """Тест с отсутствующими обязательными полями"""
        # Отсутствует name
        product_data = {
            "category_id": 1,
            "country_id": 1,
            "brand_id": 1,
            "price": 100,
            "stock": 10,
        }
        
        # Должна быть ошибка валидации
        with pytest.raises(ValidationError) as exc_info:
            ProductAddSchema(**product_data)
        
        # Проверяем, что ошибка именно о пропущенном поле name
        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "name" for error in errors)
    
    def test_product_add_schema_invalid_types(self):
        """Тест с неверными типами данных"""
        # price должен быть int, не str
        product_data = {
            "name": "Test Product",
            "category_id": 1,
            "country_id": 1,
            "brand_id": 1,
            "price": "not_an_integer",
            "stock": 10,
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProductAddSchema(**product_data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "price" for error in errors)
    
    def test_product_schema_from_add_schema(self):
        """Тест преобразования из ProductAddSchema в ProductSchema"""
        add_data = {
            "name": "Test Product",
            "category_id": 1,
            "country_id": 1,
            "brand_id": 1,
            "price": 100,
            "stock": 10,
        }
        
        product_add = ProductAddSchema(**add_data)
        
        # Создаем ProductSchema из ProductAddSchema + id
        product_schema_data = product_add.model_dump()
        product_schema_data["id"] = 1
        
        product = ProductSchema(**product_schema_data)
        
        # Проверяем, что все поля перенесены и добавлен id
        assert product.id == 1
        assert product.name == "Test Product"
        assert product.category_id == 1
    
    def test_product_update_schema(self):
        """Тест схемы обновления продукта"""
        # В схеме обновления все поля опциональные
        update_data = {
            "name": "Updated Product",
            "price": 200
        }
        
        update_schema = ProductUpdateSchema(**update_data)
        
        # Проверяем заполненные поля
        assert update_schema.name == "Updated Product"
        assert update_schema.price == 200
        
        # Проверяем, что остальные поля None
        assert update_schema.category_id is None
        assert update_schema.country_id is None
        
        # Проверяем, что пустой объект обновления тоже валидный
        empty_update = ProductUpdateSchema()
        assert empty_update.name is None
        assert empty_update.price is None


class TestCategorySchemas:
    """Тесты для схем категорий"""
    
    def test_category_add_schema(self):
        """Тест создания категории"""
        category_data = {
            "name": "Test Category",
            "slug": "test-category"
        }
        
        category = CategoryAddSchema(**category_data)
        
        assert category.name == "Test Category"
        assert category.slug == "test-category"
    
    def test_category_schema(self):
        """Тест схемы категории с id"""
        category_data = {
            "id": 1,
            "name": "Test Category",
            "slug": "test-category"
        }
        
        category = CategorySchema(**category_data)
        
        assert category.id == 1
        assert category.name == "Test Category"
        assert category.slug == "test-category"
    
    def test_category_invalid_slug(self):
        """Тест с невалидным slug (если есть валидация)"""
        # Этот тест может потребовать доработки, если у вас есть конкретная 
        # валидация для поля slug
        category_data = {
            "name": "Test Category",
            "slug": "test category with spaces"  # slug не должен содержать пробелы
        }
        
        # Если в модели есть валидатор slug, то этот тест должен падать
        # Но поскольку в текущей модели нет явной валидации slug, он пройдет
        category = CategoryAddSchema(**category_data)
        assert category.slug == "test category with spaces" 