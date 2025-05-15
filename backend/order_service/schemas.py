"""Схемы Pydantic для сервиса заказов."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict

# Перечисления
class OrderStatusEnum(str, Enum):
    """Перечисление статусов заказа."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"


class SuggestRequest(BaseModel):
    """Запрос для подсказок."""
    query: str = Field(..., description="Строка для подсказки")
    from_bound: dict = Field(None, example={"value": "city"})
    to_bound: dict = Field(None, example={"value": "city"})
    locations: list = Field(None, description="Фильтры местоположения")

# Базовые модели
class AddressBase(BaseModel):
    """Базовая модель адреса."""
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
    """Базовая модель элемента заказа."""
    product_id: int
    quantity: int = Field(..., gt=0)

# Схемы для промокодов
class PromoCodeBase(BaseModel):
    """Базовая схема для промокода."""
    code: str = Field(..., min_length=3, max_length=50)
    discount_percent: Optional[int] = Field(None, ge=1, le=100, description="Скидка в процентах (от 1 до 100)")
    discount_amount: Optional[int] = Field(None, ge=1, description="Фиксированная скидка в рублях")
    valid_until: datetime = Field(..., description="Срок действия промокода")
    is_active: bool = True
    
    @model_validator(mode='after')
    def validate_discount(self):
        """Валидатор для проверки, что указан только один тип скидки."""
        if (self.discount_percent is None and self.discount_amount is None) or \
           (self.discount_percent is not None and self.discount_amount is not None):
            raise ValueError("Необходимо указать либо процент скидки, либо фиксированную сумму скидки")
        return self

# Модели для создания
class AddressCreate(AddressBase):
    """Модель для создания адреса."""
    pass

class ShippingAddressCreate(AddressBase):
    """Модель для создания адреса доставки."""
    pass

class BillingAddressCreate(AddressBase):
    """Модель для создания адреса для выставления счета."""
    pass

class OrderItemCreate(OrderItemBase):
    """Модель для создания элемента заказа."""
    pass

class OrderCreate(BaseModel):
    """Модель для создания заказа."""
    items: List[OrderItemCreate] = Field(..., min_items=1)
    
    # Данные о клиенте и доставке
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=11, max_length=12)
    delivery_address: str = Field(..., min_length=5, max_length=255)
    comment: Optional[str] = None
    
    # Информация о типе доставки
    delivery_type: str = Field(..., description="Тип доставки: boxberry_pickup_point, boxberry_courier, cdek_pickup_point, cdek_courier")
    boxberry_point_address: Optional[str] = Field(None, description="Адрес пункта выдачи")
    
    # Стоимость доставки
    delivery_cost: Optional[int] = Field(None, description="Стоимость доставки")
    
    # Информация о способе оплаты
    is_payment_on_delivery: Optional[bool] = Field(True, description="Оплата при получении")
    
    # Поле для промокода
    promo_code: Optional[str] = Field(None, min_length=3, max_length=50)

    # Согласие на получение уведомлений для неавторизованных пользователей
    receive_notifications: Optional[bool] = None
    
    # Согласие на обработку персональных данных
    personal_data_agreement: bool = Field(..., description="Согласие на обработку персональных данных")
    
    @field_validator('phone')
    def validate_phone_format(cls, v):
        """Валидирует формат номера телефона для админского создания заказа.
        
        Args:
            v (str): Номер телефона для валидации
            
        Returns:
            str: Валидный номер телефона
            
        Raises:
            ValueError: Если номер не соответствует формату
        """
        if not (v.startswith('+7') or v.startswith('8')):
            raise ValueError('Телефон должен начинаться с "+7" или "8"')
        if not (v.startswith('+7') and len(v) == 12) and not (v.startswith('8') and len(v) == 11):
            raise ValueError('Неверный формат телефона. Примеры: 89999999999 или +79999999999')
        # Проверяем, что строка состоит только из цифр (кроме символа '+')
        if not all(c.isdigit() for c in v.replace('+', '')):
            raise ValueError('Телефон должен содержать только цифры')
        return v
    
    @field_validator('full_name', 'delivery_address', 'comment', 'promo_code')
    def validate_text_fields(cls, v, info):
        """Валидирует текстовые поля для защиты от SQL-инъекций и XSS-атак.
        
        Args:
            v (str): Значение для валидации
            info: Информация о поле
            
        Returns:
            str: Очищенное значение
            
        Raises:
            ValueError: Если значение содержит потенциально опасные символы
        """
        if v is None:
            return v
            
        # Список опасных символов и паттернов для SQL-инъекций
        sql_patterns = [
            "'", "--", "/*", "*/", "@@", "@", 
            "EXEC", "EXECUTE", "INSERT", "SELECT", "DELETE", "UPDATE", 
            "DROP", "ALTER", "CREATE", "TRUNCATE", "UNION", 
            "1=1", "OR 1=1"
        ]
        
        # Список опасных паттернов для XSS-атак
        xss_patterns = [
            "<script", "</script>", "javascript:", "onload=", "onerror=",
            "<img", "<iframe", "<svg", "<embed", "<object", 
            "eval(", "document.", "window."
        ]
        
        # Проверка на SQL-инъекции
        for pattern in sql_patterns:
            if pattern.upper() in v.upper():
                raise ValueError(f"Недопустимое значение в поле {info.field_name}: обнаружен паттерн SQL-инъекции")
                
        # Проверка на XSS-атаки
        for pattern in xss_patterns:
            if pattern.lower() in v.lower():
                raise ValueError(f"Недопустимое значение в поле {info.field_name}: обнаружен паттерн XSS-атаки")
                
        return v
    
    @model_validator(mode='after')
    def validate_all_fields(self):
        """Дополнительная валидация всех полей заказа.
        
        Returns:
            OrderCreate: Валидный объект заказа
        """
        # Дополнительные проверки для всех полей
        text_fields = {
            'full_name': self.full_name,
            'delivery_address': self.delivery_address
        }
        
        if self.comment:
            text_fields['comment'] = self.comment
            
        if self.promo_code:
            text_fields['promo_code'] = self.promo_code
        
        # Проверка на максимальную длину для предотвращения атак на переполнение буфера
        for field_name, value in text_fields.items():
            if len(value) > 1000:  # Дополнительное ограничение длины
                raise ValueError(f"Поле {field_name} слишком длинное")
        
        return self

    @field_validator('delivery_type')
    def validate_delivery_type(cls, v):
        """Валидирует тип доставки для создания заказа.
        
        Args:
            v (str): Тип доставки для валидации
            
        Returns:
            str: Валидный тип доставки
            
        Raises:
            ValueError: Если тип доставки не соответствует допустимым значениям
        """
        if not v:
            raise ValueError("Тип доставки обязателен. Выберите способ доставки")
            
        valid_types = ["boxberry_pickup_point", "boxberry_courier", "cdek_pickup_point", "cdek_courier"]
        if v not in valid_types:
            raise ValueError(f"Тип доставки должен быть одним из: {', '.join(valid_types)}")
        return v

class OrderStatusCreate(BaseModel):
    """Модель для создания статуса заказа."""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    color: str = Field('#808080', pattern=r'^#[0-9A-Fa-f]{6}$')
    allow_cancel: bool = True
    is_final: bool = False
    sort_order: int = 0

class OrderStatusHistoryCreate(BaseModel):
    """Модель для создания истории статусов заказа."""
    status_id: int
    notes: Optional[str] = None

class PromoCodeCreate(PromoCodeBase):
    """Схема для создания промокода."""
    pass

# Модели для обновления
class AddressUpdate(BaseModel):
    """Модель для обновления адреса."""
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
    """Модель для обновления заказа."""
    status_id: Optional[int] = None
    
    # Данные о клиенте и доставке
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=11, max_length=12)
    delivery_address: Optional[str] = Field(None, min_length=5, max_length=255)
    comment: Optional[str] = None
    
    # Информация о типе доставки
    delivery_type: Optional[str] = Field(None, description="Тип доставки: boxberry_pickup_point, boxberry_courier, cdek_pickup_point, cdek_courier")
    boxberry_point_address: Optional[str] = Field(None, description="Адрес пункта выдачи")
    
    is_paid: Optional[bool] = None
    
    @field_validator('phone')
    def validate_phone(cls, v):
        """Валидирует формат номера телефона для обновления заказа.
        
        Args:
            v (str): Номер телефона для валидации
            
        Returns:
            str: Валидный номер телефона или None
            
        Raises:
            ValueError: Если номер не соответствует формату
        """
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

    @field_validator('delivery_type')
    def validate_delivery_type(cls, v):
        """Валидирует тип доставки для обновления заказа.
        
        Args:
            v (str): Тип доставки для валидации
            
        Returns:
            str: Валидный тип доставки
            
        Raises:
            ValueError: Если тип доставки не соответствует допустимым значениям
        """
        if v is None:
            return v
            
        valid_types = ["boxberry_pickup_point", "boxberry_courier", "cdek_pickup_point", "cdek_courier"]
        if v not in valid_types:
            raise ValueError(f"Тип доставки должен быть одним из: {', '.join(valid_types)}")
        return v

class OrderStatusUpdate(BaseModel):
    """Модель для обновления статуса заказа."""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    allow_cancel: Optional[bool] = None
    is_final: Optional[bool] = None
    sort_order: Optional[int] = None

class PromoCodeUpdate(BaseModel):
    """Схема для обновления промокода."""
    code: Optional[str] = Field(None, min_length=3, max_length=50)
    discount_percent: Optional[int] = Field(None, ge=1, le=100, description="Скидка в процентах (от 1 до 100)")
    discount_amount: Optional[int] = Field(None, ge=1, description="Фиксированная скидка в рублях")
    valid_until: Optional[datetime] = Field(None, description="Срок действия промокода")
    is_active: Optional[bool] = None
    
    @model_validator(mode='after')
    def validate_discount(self):
        """Валидатор для проверки, что не указаны оба типа скидки одновременно."""
        if self.discount_percent is not None and self.discount_amount is not None:
            raise ValueError("Нельзя указать одновременно и процент скидки, и фиксированную сумму скидки")
        return self

# Модели для ответов
class OrderStatusResponse(BaseModel):
    """Модель ответа со статусом заказа."""
    id: int
    name: str
    description: Optional[str] = None
    color: str
    allow_cancel: bool
    is_final: bool
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusHistoryResponse(BaseModel):
    """Модель ответа с историей статусов заказа."""
    id: int
    order_id: int
    status_id: int
    status: OrderStatusResponse
    changed_at: datetime
    changed_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AddressResponse(AddressBase):
    """Модель ответа с адресом."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ShippingAddressResponse(AddressResponse):
    """Модель ответа с адресом доставки."""
    pass

class BillingAddressResponse(AddressResponse):
    """Модель ответа с адресом для выставления счета."""
    pass

class PromoCodeResponse(PromoCodeBase):
    """Схема для ответа с промокодом."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrderItemResponse(OrderItemBase):
    """Модель ответа с элементом заказа."""
    id: int
    order_id: int
    product_name: str
    product_price: int
    total_price: int
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Схемы для редактирования товаров в заказе
class OrderItemUpdate(BaseModel):
    """Схема для обновления количества товара в заказе."""
    quantity: int = Field(..., gt=0)

class OrderItemAdd(BaseModel):
    """Схема для добавления товара в заказ."""
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

class OrderItemsUpdate(BaseModel):
    """Схема для массового обновления элементов заказа."""
    items_to_add: Optional[List[OrderItemAdd]] = Field(None, description="Товары для добавления в заказ")
    items_to_update: Optional[Dict[int, int]] = Field(None, description="Словарь {id_товара_в_заказе: новое_количество}")
    items_to_remove: Optional[List[int]] = Field(None, description="ID товаров в заказе для удаления")

class PromoCodeCheckRequest(BaseModel):
    """Схема для запроса проверки промокода."""
    code: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., description="Email пользователя для проверки использования")
    phone: str = Field(..., min_length=11, max_length=12, description="Телефон пользователя для проверки использования")

class PromoCodeCheckResponse(BaseModel):
    """Схема для ответа на проверку промокода."""
    is_valid: bool
    message: str
    discount_percent: Optional[int] = None
    discount_amount: Optional[int] = None
    promo_code: Optional[PromoCodeResponse] = None

class OrderResponse(BaseModel):
    """Модель ответа с заказом."""
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
    delivery_address: str
    comment: Optional[str] = None
    
    # Информация о типе доставки
    delivery_type: str = Field(..., description="Тип доставки: boxberry_pickup_point, boxberry_courier, cdek_pickup_point, cdek_courier")
    boxberry_point_address: Optional[str] = None
    boxberry_point_id: Optional[str] = None
    delivery_cost: Optional[int] = None
    
    # Информация о способе оплаты
    is_payment_on_delivery: Optional[bool] = True
    
    is_paid: bool
    personal_data_agreement: Optional[bool] = None
    
    # Согласие на получение уведомлений для неавторизованных пользователей
    receive_notifications: Optional[bool] = None
    
    items: List[OrderItemResponse] = []
    
    order_number: str
    
    model_config = ConfigDict(from_attributes=True)

class OrderResponseWithPromo(OrderResponse):
    """Расширенный ответ заказа с информацией о промокоде (создается вручную)."""
    promo_code: Optional[PromoCodeResponse] = None

class OrderDetailResponse(OrderResponse):
    """Детальный ответ с заказом."""
    status_history: List[OrderStatusHistoryResponse] = []

class OrderDetailResponseWithPromo(OrderDetailResponse):
    """Расширенный детальный ответ заказа с информацией о промокоде (создается вручную)."""
    promo_code: Optional[PromoCodeResponse] = None

# Схема ответа об изменении товаров в заказе
class OrderItemsUpdateResponse(BaseModel):
    """Схема ответа об изменении товаров в заказе."""
    success: bool
    order: Optional[OrderResponse] = None
    errors: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

# Модели для пагинации и фильтрации
class PaginatedResponse(BaseModel):
    """Модель для пагинированного ответа."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    
    @field_validator('pages', mode='before')
    def calculate_pages(cls, v, info):
        """Вычисляет общее количество страниц для пагинации.
        
        Args:
            v: Значение поля pages
            info: Информация о валидации
            
        Returns:
            int: Количество страниц
        """
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
        logger.info("Вычисление страниц: total=%d, size=%d, pages=%d", total, size, pages)
        
        return pages

class OrderFilterParams(BaseModel):
    """Параметры фильтрации заказов."""
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
    """Модель статистики заказов."""
    total_orders: int
    total_revenue: int
    average_order_value: float
    orders_by_status: Dict[str, int]
    orders_by_payment_method: Dict[str, int]
    canceled_orders_revenue: int = 0  # Сумма отмененных заказов
    
    model_config = ConfigDict(from_attributes=True)

class BatchStatusUpdate(BaseModel):
    """Модель для массового обновления статусов."""
    order_ids: List[int]
    status_id: int
    notes: Optional[str] = None

# Схемы для статусов оплаты
class PaymentStatusBase(BaseModel):
    """Базовая модель статуса оплаты."""
    name: str
    description: Optional[str] = None
    color: str = "#3498db"  # Цвет по умолчанию (синий)
    is_paid: bool = False  # Флаг, указывающий, считается ли статус "оплаченным"
    sort_order: int = 0

class PaymentStatusCreate(PaymentStatusBase):
    """Модель для создания статуса оплаты."""
    pass

class PaymentStatusUpdate(BaseModel):
    """Модель для обновления статуса оплаты."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_paid: Optional[bool] = None
    sort_order: Optional[int] = None

class PaymentStatusResponse(PaymentStatusBase):
    """Модель ответа со статусом оплаты."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderItemSchema(BaseModel):
    """Схема для элемента заказа."""
    id: int
    product_id: int
    product_name: str
    product_price: int
    quantity: int
    total_price: int
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusSchema(BaseModel):
    """Схема для отображения статуса заказа."""
    id: int
    name: str
    description: Optional[str] = None
    color: str
    allow_cancel: bool
    is_final: bool
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)

class OrderStatusHistorySchema(BaseModel):
    """Схема для истории статусов заказа."""
    id: int
    order_id: int
    status_id: int
    changed_at: datetime
    changed_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[OrderStatusSchema] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderSchema(BaseModel):
    """Схема для отображения заказа."""
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
    personal_data_agreement: bool = Field(..., description="Согласие на обработку персональных данных")
    
    # Информация о типе доставки
    delivery_type: str = Field("standard", description="Тип доставки: standard, boxberry")
    boxberry_point_id: Optional[str] = None
    boxberry_point_address: Optional[str] = None
    boxberry_city_code: Optional[str] = None
    
    order_number: str
    status: Optional[OrderStatusSchema] = None
    items: List[OrderItemSchema] = []
    status_history: List[OrderStatusHistorySchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class AdminOrderCreate(BaseModel):
    """Схема для создания заказа администратором."""
    items: List[OrderItemCreate] = Field(..., min_items=1)
    
    # Данные о клиенте и доставке
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=11, max_length=12)
    delivery_address: str = Field(..., min_length=5, max_length=255)
    comment: Optional[str] = None
    
    # Информация о типе доставки
    delivery_type: str = Field(..., description="Тип доставки: boxberry_pickup_point, boxberry_courier, cdek_pickup_point, cdek_courier")
    boxberry_point_address: Optional[str] = Field(None, description="Адрес пункта выдачи")
    
    # Стоимость доставки
    delivery_cost: Optional[int] = Field(None, description="Стоимость доставки в рублях")
    
    # Информация о способе оплаты
    is_payment_on_delivery: Optional[bool] = Field(True, description="Оплата при получении")
    
    # Поле для привязки к пользователю (опционально)
    user_id: Optional[int] = None
    
    # Поле для установки статуса (опционально)
    status_id: Optional[int] = None
    
    # Флаг оплаты (опционально)
    is_paid: bool = False
    
    # Поле для промокода
    promo_code: Optional[str] = Field(None, min_length=3, max_length=50)
    
    @field_validator('phone')
    def validate_phone_format(cls, v):
        """Валидирует формат номера телефона для админского создания заказа.
        
        Args:
            v (str): Номер телефона для валидации
            
        Returns:
            str: Валидный номер телефона
            
        Raises:
            ValueError: Если номер не соответствует формату
        """
        if not (v.startswith('+7') or v.startswith('8')):
            raise ValueError('Телефон должен начинаться с "+7" или "8"')
        if not (v.startswith('+7') and len(v) == 12) and not (v.startswith('8') and len(v) == 11):
            raise ValueError('Неверный формат телефона. Примеры: 89999999999 или +79999999999')
        # Проверяем, что строка состоит только из цифр (кроме символа '+')
        if not all(c.isdigit() for c in v.replace('+', '')):
            raise ValueError('Телефон должен содержать только цифры')
        return v

    @field_validator('delivery_type')
    def validate_delivery_type(cls, v):
        """Валидирует тип доставки для создания заказа администратором.
        
        Args:
            v (str): Тип доставки для валидации
            
        Returns:
            str: Валидный тип доставки
            
        Raises:
            ValueError: Если тип доставки не соответствует допустимым значениям
        """
        if not v:
            raise ValueError("Тип доставки обязателен. Выберите способ доставки")
            
        valid_types = ["boxberry_pickup_point", "boxberry_courier", "cdek_pickup_point", "cdek_courier"]
        if v not in valid_types:
            raise ValueError(f"Тип доставки должен быть одним из: {', '.join(valid_types)}")
        return v
