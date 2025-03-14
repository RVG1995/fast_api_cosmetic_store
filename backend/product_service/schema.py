from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
import re

# Функция валидации slug
def validate_slug(slug: str) -> str:
    if not slug:
        raise ValueError("Slug не может быть пустым")
    if ' ' in slug:
        raise ValueError("Slug не может содержать пробелы")
    # Проверяем, что slug содержит только допустимые символы
    if not re.match(r'^[a-z0-9-]+$', slug):
        raise ValueError("Slug может содержать только строчные буквы латинского алфавита, цифры и дефисы")
    return slug

class CategoryAddSchema(BaseModel):
    name: str
    slug: str

    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        return validate_slug(v)

class CategorySchema(CategoryAddSchema):
    id:int


class CategoryUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CountryAddSchema(BaseModel):
    name: str
    slug: str
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        return validate_slug(v)

class CountrySchema(CountryAddSchema):
    id:int

class CountryUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BrandAddSchema(BaseModel):
    name: str
    slug: str
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        return validate_slug(v)

class BrandSchema(BrandAddSchema):
    id:int

class BrandUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SubCategoryAddSchema(BaseModel):
    name: str
    slug: str
    category_id: int
    
    # Валидация slug
    @field_validator('slug')
    def slug_must_be_valid(cls, v):
        return validate_slug(v)

class SubCategorySchema(SubCategoryAddSchema):
    id:int


class SubCategoryUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] =None
    
    model_config = ConfigDict(from_attributes=True)

class ProductAddSchema(BaseModel):
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
    items: List[ProductSchema]
    total: int
    offset: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)