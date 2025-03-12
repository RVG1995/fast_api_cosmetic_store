from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class CategoryAddSchema(BaseModel):
    name: str
    slug: str

class CategorySchema(CategoryAddSchema):
    id:int


class CategoryUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CountryAddSchema(BaseModel):
    name: str
    slug: str

class CountrySchema(CountryAddSchema):
    id:int

class CountryUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class BrandAddSchema(BaseModel):
    name: str
    slug: str

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
    skip: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)