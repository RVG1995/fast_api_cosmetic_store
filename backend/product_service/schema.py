"""
Схемы Pydantic для product_service: категории, бренды, подкатегории, продукты.
"""
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
import re

# Функция валидации slug
def validate_slug(slug: str) -> str:
    """Валидация slug."""
    if not slug:
        raise ValueError("Slug не может быть пустым")
    if ' ' in slug:
        raise ValueError("Slug не может содержать пробелы")
    # Проверяем, что slug содержит только допустимые символы
    if not re.match(r'^[a-z0-9-]+$', slug):
        raise ValueError("Slug может содержать только строчные буквы латинского алфавита, цифры и дефисы")
    return slug

class CategoryAddSchema(BaseModel):
    """Схема добавления категории."""
    name: str
    slug: str

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидация slug."""
        return validate_slug(v)

class CategorySchema(CategoryAddSchema):
    """Схема категории."""
    id:int


class CategoryUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CountryAddSchema(BaseModel):
    """Схема добавления страны."""
    name: str
    slug: str
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидация slug."""
        return validate_slug(v)

class CountrySchema(CountryAddSchema):
    """Схема страны."""
    id:int

class CountryUpdateSchema(BaseModel):
    """Схема обновления страны."""
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BrandAddSchema(BaseModel):
    """Схема добавления бренда."""
    name: str
    slug: str
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидация slug."""
        return validate_slug(v)

class BrandSchema(BrandAddSchema):
    """Схема бренда."""
    id:int

class BrandUpdateSchema(BaseModel):
    """Схема обновления бренда."""
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SubCategoryAddSchema(BaseModel):
    """Схема добавления подкатегории."""
    name: str
    slug: str
    category_id: int
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        """Валидация slug."""
        return validate_slug(v)

class SubCategorySchema(SubCategoryAddSchema):
    """Схема подкатегории."""
    id:int


class SubCategoryUpdateSchema(BaseModel):
    """Схема обновления подкатегории."""
    name: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] =None
    
    model_config = ConfigDict(from_attributes=True)

class ProductAddSchema(BaseModel):
    """Схема добавления продукта."""
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
    """Схема продукта."""
    id:int

    model_config = ConfigDict(from_attributes=True)

class ProductDetailSchema(ProductSchema):
    """Расширенная схема продукта с вложенными объектами связанных сущностей"""
    category: Optional[CategorySchema] = None
    subcategory: Optional[SubCategorySchema] = None
    brand: Optional[BrandSchema] = None
    country: Optional[CountrySchema] = None

    model_config = ConfigDict(from_attributes=True)

class ProductUpdateSchema(BaseModel):
    """Схема обновления продукта."""
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
    """Схема пагинированного ответа на запрос продуктов."""
    items: List[ProductSchema]
    total: int
    offset: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)
