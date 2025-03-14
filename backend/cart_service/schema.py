from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class CartItemAddSchema(BaseModel):
    """Схема для добавления товара в корзину"""
    product_id: int
    quantity: int

class CartItemUpdateSchema(BaseModel):
    """Схема для обновления количества товара в корзине"""
    quantity: int

class ProductInfoSchema(BaseModel):
    """Схема с базовой информацией о продукте"""
    id: int
    name: str
    price: int
    image: Optional[str] = None
    stock: int
    
    model_config = ConfigDict(from_attributes=True)

class CartItemSchema(BaseModel):
    """Схема для отображения элемента корзины"""
    id: int
    product_id: int
    quantity: int
    added_at: datetime
    updated_at: datetime
    
    # Дополнительная информация о продукте (будет запрашиваться из сервиса продуктов)
    product: Optional[ProductInfoSchema] = None
    
    model_config = ConfigDict(from_attributes=True)

class CartSchema(BaseModel):
    """Схема для отображения корзины"""
    id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[CartItemSchema] = []
    
    # Дополнительные расчетные поля
    total_items: int = 0
    total_price: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class CartSummarySchema(BaseModel):
    """Упрощенная схема корзины для отображения в интерфейсе"""
    total_items: int
    total_price: int
    
    model_config = ConfigDict(from_attributes=True)

class CartResponseSchema(BaseModel):
    """Схема ответа для операций с корзиной"""
    success: bool
    message: str
    cart: Optional[CartSchema] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CleanupResponseSchema(BaseModel):
    """Схема для ответа об очистке устаревших корзин"""
    success: bool
    deleted_count: int
    message: str
    
    model_config = ConfigDict(from_attributes=True)

class ShareCartRequestSchema(BaseModel):
    """Схема запроса для публикации корзины"""
    expires_in_hours: Optional[int] = 24  # По умолчанию 24 часа

class ShareCartResponseSchema(BaseModel):
    """Схема ответа для публикации корзины"""
    success: bool
    message: str
    share_code: Optional[str] = None
    share_url: Optional[str] = None
    error: Optional[str] = None

class LoadSharedCartSchema(BaseModel):
    """Схема запроса для загрузки опубликованной корзины"""
    share_code: str
    merge_strategy: Optional[str] = "replace"  # replace, merge_add, merge_max 