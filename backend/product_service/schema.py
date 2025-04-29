"""Схемы Pydantic для валидации данных продуктов и связанных сущностей."""

import re
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator

# Функция валидации slug
def validate_slug(slug: str) -> str:
    """Проверяет корректность slug и возвращает его, если он валиден.
    
    Args:
        slug: Строка для валидации
        
    Returns:
        Валидный slug
        
    Raises:
        ValueError: Если slug не соответствует требованиям
    """
    if not slug:
        raise ValueError("Slug не может быть пустым")
    if ' ' in slug:
        raise ValueError("Slug не может содержать пробелы")
    # Проверяем, что slug содержит только допустимые символы
    if not re.match(r'^[a-z0-9-]+$', slug):
        raise ValueError("Slug может содержать только строчные буквы латинского алфавита, цифры и дефисы")
    return slug

class CategoryAddSchema(BaseModel):
    """Схема для добавления категории."""
    name: str
    slug: str

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class CategorySchema(CategoryAddSchema):
    """Схема категории с ID."""
    id:int

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class CategoryUpdateSchema(BaseModel):
    """Схема для обновления категории."""
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CountryAddSchema(BaseModel):
    """Схема для добавления страны."""
    name: str
    slug: str
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class CountrySchema(CountryAddSchema):
    """Схема страны с ID."""
    id:int

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class CountryUpdateSchema(BaseModel):
    """Схема для обновления страны."""
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BrandAddSchema(BaseModel):
    """Схема для добавления бренда."""
    name: str
    slug: str
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class BrandSchema(BrandAddSchema):
    """Схема бренда с ID."""
    id:int

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class BrandUpdateSchema(BaseModel):
    """Схема для обновления бренда."""
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SubCategoryAddSchema(BaseModel):
    """Схема для добавления подкатегории."""
    name: str
    slug: str
    category_id: int
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class SubCategorySchema(SubCategoryAddSchema):
    """Схема подкатегории с ID."""
    id:int

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидирует slug с помощью validate_slug."""
        return validate_slug(v)

class SubCategoryUpdateSchema(BaseModel):
    """Схема для обновления подкатегории."""
    name: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] =None
    
    model_config = ConfigDict(from_attributes=True)

class ProductAddSchema(BaseModel):
    """Схема для добавления продукта."""
    name: str
    category_id: Optional[int] = None
    country_id: int
    brand_id: int
    subcategory_id: Optional[int] = None
    price: int
    description: Optional[str] = None
    stock: int
    image: Optional[str] = None

class ProductSchema(ProductAddSchema):
    """Схема продукта с ID."""
    id:int

    model_config = ConfigDict(from_attributes=True)

class ProductDetailSchema(ProductSchema):
    """Расширенная схема продукта с вложенными объектами связанных сущностей."""
    category: Optional[CategorySchema] = None
    subcategory: Optional[SubCategorySchema] = None
    brand: Optional[BrandSchema] = None
    country: Optional[CountrySchema] = None

    model_config = ConfigDict(from_attributes=True)

class ProductUpdateSchema(BaseModel):
    """Схема для обновления продукта."""
    name: Optional[str] = None
    category_id: Optional[int] = None
    country_id: Optional[int] = None
    brand_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    price: Optional[int] = None
    description: Optional[str] = None
    stock: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedProductResponse(BaseModel):
    """Схема для пагинированного ответа с продуктами."""
    items: List[ProductSchema]
    total: int
    offset: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)
