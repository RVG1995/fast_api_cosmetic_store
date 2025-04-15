from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict
from enum import Enum
import logging

# Перечисления
class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"

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

# Схемы для промокодов
class PromoCodeBase(BaseModel):
    """Базовая схема для промокода"""
    code: str = Field(..., min_length=3, max_length=50)
    discount_percent: Optional[int] = Field(None, ge=1, le=100, description="Скидка в процентах (от 1 до 100)")
    discount_amount: Optional[int] = Field(None, ge=1, description="Фиксированная скидка в рублях")
    valid_until: datetime = Field(..., description="Срок действия промокода")
    is_active: bool = True
    
    @model_validator(mode='after')
    def validate_discount(self):
        """Валидатор для проверки, что указан только один тип скидки"""
        if (self.discount_percent is None and self.discount_amount is None) or \
           (self.discount_percent is not None and self.discount_amount is not None):
            raise ValueError("Необходимо указать либо процент скидки, либо фиксированную сумму скидки")
        return self

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
    
    # Данные о клиенте и доставке
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=11, max_length=12)
    region: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    street: str = Field(..., min_length=5, max_length=255)
    comment: Optional[str] = None
    
    # Поле для промокода
    promo_code: Optional[str] = Field(None, min_length=3, max_length=50)
    
    @field_validator('phone')
    def validate_phone_format(cls, v):
        if not (v.startswith('+7') or v.startswith('8')):
            raise ValueError('Телефон должен начинаться с "+7" или "8"')
        if not (v.startswith('+7') and len(v) == 12) and not (v.startswith('8') and len(v) == 11):
            raise ValueError('Неверный формат телефона. Примеры: 89999999999 или +79999999999')
        # Проверяем, что строка состоит только из цифр (кроме символа '+')
        if not all(c.isdigit() for c in v.replace('+', '')):
            raise ValueError('Телефон должен содержать только цифры')
        return v

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

class PromoCodeCreate(PromoCodeBase):
    """Схема для создания промокода"""
    pass

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
    status_id: Optional[int] = None
    
    # Данные о клиенте и доставке
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=11, max_length=12)
    region: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    street: Optional[str] = Field(None, min_length=5, max_length=255)
    comment: Optional[str] = None
    
    is_paid: Optional[bool] = None
    
    @field_validator('phone')
    def validate_phone(cls, v):
        if v is None:
            return v
        if not (v.startswith('+7') or v.startswith('8')):
            raise ValueError('Телефон должен начинаться с +7 или 8')
        if not (v.startswith('+7') and len(v) == 12) and not (v.startswith('8') and len(v) == 11):
            raise ValueError('Неверный формат телефона. Примеры: 89999999999 или +79999999999')
        # Проверяем, что строка состоит только из цифр (кроме символа '+')
        if not all(c.isdigit() for c in v.replace('+', '')):
            raise ValueError('Телефон должен содержать только цифры')
        return v

class OrderStatusUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    allow_cancel: Optional[bool] = None
    is_final: Optional[bool] = None
    sort_order: Optional[int] = None

class PromoCodeUpdate(BaseModel):
    """Схема для обновления промокода"""
    code: Optional[str] = Field(None, min_length=3, max_length=50)
    discount_percent: Optional[int] = Field(None, ge=1, le=100, description="Скидка в процентах (от 1 до 100)")
    discount_amount: Optional[int] = Field(None, ge=1, description="Фиксированная скидка в рублях")
    valid_until: Optional[datetime] = Field(None, description="Срок действия промокода")
    is_active: Optional[bool] = None
    
    @model_validator(mode='after')
    def validate_discount(self):
        """Валидатор для проверки, что не указаны оба типа скидки одновременно"""
        if self.discount_percent is not None and self.discount_amount is not None:
            raise ValueError("Нельзя указать одновременно и процент скидки, и фиксированную сумму скидки")
        return self

# Модели для ответов
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

class PromoCodeResponse(PromoCodeBase):
    """Схема для ответа с промокодом"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    product_name: str
    product_price: int
    total_price: int
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Схемы для редактирования товаров в заказе
class OrderItemUpdate(BaseModel):
    """Схема для обновления количества товара в заказе"""
    quantity: int = Field(..., gt=0)

class OrderItemAdd(BaseModel):
    """Схема для добавления товара в заказ"""
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

class OrderItemsUpdate(BaseModel):
    """Схема для массового обновления элементов заказа"""
    items_to_add: Optional[List[OrderItemAdd]] = Field(None, description="Товары для добавления в заказ")
    items_to_update: Optional[Dict[int, int]] = Field(None, description="Словарь {id_товара_в_заказе: новое_количество}")
    items_to_remove: Optional[List[int]] = Field(None, description="ID товаров в заказе для удаления")

class PromoCodeCheckRequest(BaseModel):
    """Схема для запроса проверки промокода"""
    code: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., description="Email пользователя для проверки использования")
    phone: str = Field(..., min_length=11, max_length=12, description="Телефон пользователя для проверки использования")

class PromoCodeCheckResponse(BaseModel):
    """Схема для ответа на проверку промокода"""
    is_valid: bool
    message: str
    discount_percent: Optional[int] = None
    discount_amount: Optional[int] = None
    promo_code: Optional[PromoCodeResponse] = None

class OrderResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    status_id: int
    status: OrderStatusResponse
    created_at: datetime
    updated_at: datetime
    total_price: int
    
    # Данные о промокоде и скидке
    promo_code_id: Optional[int] = None
    discount_amount: Optional[int] = None
    
    # Данные о клиенте и доставке
    full_name: str
    email: Optional[str] = None
    phone: str
    region: str
    city: str
    street: str
    comment: Optional[str] = None
    
    is_paid: bool
    items: List[OrderItemResponse] = []
    
    order_number: str
    
    model_config = ConfigDict(from_attributes=True)

class OrderResponseWithPromo(OrderResponse):
    """Расширенный ответ заказа с информацией о промокоде (создается вручную)"""
    promo_code: Optional[PromoCodeResponse] = None

class OrderDetailResponse(OrderResponse):
    status_history: List[OrderStatusHistoryResponse] = []

class OrderDetailResponseWithPromo(OrderDetailResponse):
    """Расширенный детальный ответ заказа с информацией о промокоде (создается вручную)"""
    promo_code: Optional[PromoCodeResponse] = None

# Схема ответа об изменении товаров в заказе
class OrderItemsUpdateResponse(BaseModel):
    success: bool
    order: Optional[OrderResponse] = None
    errors: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

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
        
        # Предотвращаем деление на ноль
        if size <= 0:
            size = 1
        
        # Вычисляем количество страниц
        pages = (total + size - 1) // size
        
        # Логирование результата вычисления
        logger = logging.getLogger("pagination")
        logger.info(f"Вычисление страниц: total={total}, size={size}, pages={pages}")
        
        return pages

class OrderFilterParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    status_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    id: Optional[int] = None
    date_from: Optional[str] = None  # Дата начала периода в формате YYYY-MM-DD
    date_to: Optional[str] = None    # Дата окончания периода в формате YYYY-MM-DD
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

class BatchStatusUpdate(BaseModel):
    order_ids: List[int]
    status_id: int
    notes: Optional[str] = None

# Схемы для статусов оплаты
class PaymentStatusBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3498db"  # Цвет по умолчанию (синий)
    is_paid: bool = False  # Флаг, указывающий, считается ли статус "оплаченным"
    sort_order: int = 0

class PaymentStatusCreate(PaymentStatusBase):
    pass

class PaymentStatusUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_paid: Optional[bool] = None
    sort_order: Optional[int] = None

class PaymentStatusResponse(PaymentStatusBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True) 