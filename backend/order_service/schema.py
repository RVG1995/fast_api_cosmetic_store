from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductInfoSchema(BaseModel):
    """Схема с базовой информацией о продукте"""
    id: int
    name: str
    price: int
    image: Optional[str] = None
    stock: int
    
    model_config = ConfigDict(from_attributes=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Безопасное преобразование объекта в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "image": self.image,
            "stock": self.stock
        }

class OrderItemAddSchema(BaseModel):
    """Схема для добавления товара в заказ"""
    product_id: int
    quantity: int

class OrderItemSchema(BaseModel):
    """Схема для отображения элемента заказа"""
    id: int
    product_id: int
    product_name: str
    product_price: int
    quantity: int
    total_price: int
    
    product: Optional[ProductInfoSchema] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusSchema(BaseModel):
    """Схема для отображения статуса заказа"""
    id: int
    name: str
    description: Optional[str] = None
    color: str
    allow_cancel: bool
    is_final: bool
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusCreateSchema(BaseModel):
    """Схема для создания статуса заказа"""
    name: str
    description: Optional[str] = None
    color: str = "#808080"
    allow_cancel: bool = True
    is_final: bool = False
    sort_order: int = 0

class OrderStatusUpdateSchema(BaseModel):
    """Схема для обновления статуса заказа"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    allow_cancel: Optional[bool] = None
    is_final: Optional[bool] = None
    sort_order: Optional[int] = None

class OrderStatusHistorySchema(BaseModel):
    """Схема для отображения истории изменения статуса заказа"""
    id: int
    order_id: int
    status_id: int
    changed_at: datetime
    changed_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    
    status: Optional[OrderStatusSchema] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusChangeSchema(BaseModel):
    """Схема для изменения статуса заказа"""
    status_id: int
    notes: Optional[str] = None

class OrderCreateSchema(BaseModel):
    """Схема для создания заказа"""
    cart_id: int
    shipping_address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    notes: Optional[str] = None

class OrderUpdateSchema(BaseModel):
    """Схема для обновления заказа"""
    status_id: Optional[int] = None
    shipping_address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    notes: Optional[str] = None
    is_paid: Optional[bool] = None

class OrderSchema(BaseModel):
    """Схема для отображения заказа"""
    id: int
    user_id: int
    status_id: int
    created_at: datetime
    updated_at: datetime
    total_price: int
    shipping_address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    is_paid: bool
    
    order_number: str
    status: Optional[OrderStatusSchema] = None
    items: List[OrderItemSchema] = []
    status_history: List[OrderStatusHistorySchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class OrderDetailSchema(OrderSchema):
    """Схема для детального отображения заказа, включая историю статусов"""
    model_config = ConfigDict(from_attributes=True)

class OrderListSchema(BaseModel):
    """Схема для отображения списка заказов с пагинацией"""
    id: int
    user_id: int
    order_number: str
    created_at: datetime
    updated_at: datetime
    total_price: int
    status: Optional[OrderStatusSchema] = None
    is_paid: bool
    items_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedOrdersResponse(BaseModel):
    """Схема для ответа с пагинацией заказов"""
    items: List[OrderListSchema]
    total: int
    page: int
    limit: int
    pages: int
    
    model_config = ConfigDict(from_attributes=True)

class OrderResponseSchema(BaseModel):
    """Схема ответа для операций с заказами"""
    success: bool
    message: str
    order: Optional[OrderSchema] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class EmailTemplateSchema(BaseModel):
    """Схема шаблона электронного письма для заказа"""
    subject: str
    template: str
    
    model_config = ConfigDict(from_attributes=True)

class OrderCancelSchema(BaseModel):
    """Схема для отмены заказа"""
    reason: Optional[str] = None 