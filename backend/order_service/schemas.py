from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict
from enum import Enum

# Перечисления
class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"

class PaymentMethodEnum(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"

# Базовые модели
class AddressBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    address_line1: str = Field(..., min_length=5, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=5, max_length=20)
    is_default: bool = False

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

# Модели для создания
class AddressCreate(AddressBase):
    pass

class ShippingAddressCreate(AddressBase):
    pass

class BillingAddressCreate(AddressBase):
    pass

class OrderItemCreate(OrderItemBase):
    pass

class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_items=1)
    shipping_address: Optional[ShippingAddressCreate] = None
    shipping_address_id: Optional[int] = None
    billing_address: Optional[BillingAddressCreate] = None
    billing_address_id: Optional[int] = None
    payment_method: PaymentMethodEnum = PaymentMethodEnum.CASH_ON_DELIVERY
    contact_phone: Optional[str] = Field(None, min_length=5, max_length=20)
    contact_email: Optional[EmailStr] = None
    notes: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_addresses(self):
        shipping_address = self.shipping_address
        shipping_address_id = self.shipping_address_id
        
        if shipping_address is None and shipping_address_id is None:
            raise ValueError('Необходимо указать адрес доставки или ID существующего адреса')
        
        return self

class OrderStatusCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    color: str = Field('#808080', pattern=r'^#[0-9A-Fa-f]{6}$')
    allow_cancel: bool = True
    is_final: bool = False
    sort_order: int = 0

class OrderStatusHistoryCreate(BaseModel):
    status_id: int
    notes: Optional[str] = None

# Модели для обновления
class AddressUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    address_line1: Optional[str] = Field(None, min_length=5, max_length=255)
    address_line2: Optional[str] = None
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = None
    postal_code: Optional[str] = Field(None, min_length=3, max_length=20)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=5, max_length=20)
    is_default: Optional[bool] = None

class OrderUpdate(BaseModel):
    shipping_address_id: Optional[int] = None
    billing_address_id: Optional[int] = None
    payment_method: Optional[PaymentMethodEnum] = None
    contact_phone: Optional[str] = Field(None, min_length=5, max_length=20)
    contact_email: Optional[EmailStr] = None
    notes: Optional[str] = None
    is_paid: Optional[bool] = None

class OrderStatusUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    allow_cancel: Optional[bool] = None
    is_final: Optional[bool] = None
    sort_order: Optional[int] = None

# Модели для ответов
class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    product_name: str
    product_price: int
    total_price: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    allow_cancel: bool
    is_final: bool
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusHistoryResponse(BaseModel):
    id: int
    order_id: int
    status_id: int
    status: OrderStatusResponse
    changed_at: datetime
    changed_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AddressResponse(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ShippingAddressResponse(AddressResponse):
    pass

class BillingAddressResponse(AddressResponse):
    pass

class OrderResponse(BaseModel):
    id: int
    user_id: int
    status_id: int
    status: OrderStatusResponse
    created_at: datetime
    updated_at: datetime
    total_price: int
    shipping_address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    notes: Optional[str] = None
    is_paid: bool
    payment_method: PaymentMethodEnum
    items: List[OrderItemResponse] = []
    
    @property
    def order_number(self) -> str:
        """Получить номер заказа в формате ID + год"""
        year = self.created_at.year
        return f"{self.id}-{year}"
    
    model_config = ConfigDict(from_attributes=True)

class OrderDetailResponse(OrderResponse):
    status_history: List[OrderStatusHistoryResponse] = []

# Модели для пагинации и фильтрации
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    
    @field_validator('pages', mode='before')
    def calculate_pages(cls, v, info):
        data = info.data
        total = data.get('total', 0)
        size = data.get('size', 1)
        return (total + size - 1) // size if size > 0 else 0

class OrderFilterParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    status_id: Optional[int] = None
    user_id: Optional[int] = None
    order_by: str = "created_at"
    order_dir: str = "desc"

# Модели для статистики
class OrderStatistics(BaseModel):
    total_orders: int
    total_revenue: int
    average_order_value: float
    orders_by_status: Dict[str, int]
    orders_by_payment_method: Dict[str, int]
    
    model_config = ConfigDict(from_attributes=True) 