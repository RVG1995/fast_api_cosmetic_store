"""Роутер для интеграции с API Boxberry для получения пунктов выдачи заказов с кэшированием."""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field



# Модель для запроса расчета стоимости доставки
class DeliveryCalculationRequest(BaseModel):
    """Модель для запроса расчета стоимости доставки."""
    weight: float = Field(..., description="Вес посылки в граммах")
    order_sum: float = Field(..., description="Сумма заказа")
    pvz_code: Optional[str] = Field(None, description="Код ПВЗ (если доставка до ПВЗ)")
    delivery_sum: Optional[float] = Field(None, description="Заявленная стоимость доставки")
    height: Optional[int] = Field(None, description="Высота посылки в сантиметрах")
    width: Optional[int] = Field(None, description="Ширина посылки в сантиметрах")
    depth: Optional[int] = Field(None, description="Глубина посылки в сантиметрах")
    zip_code: Optional[int] = Field(None, description="Почтовый индекс для курьерской доставки")
    delivery_type: str = Field(..., description="Тип доставки (boxberry_pickup_point или boxberry_courier)")
    is_payment_on_delivery: bool = Field(True, description="Оплата при получении (True) или на сайте (False)")

# Модель для ответа с результатом расчета
class DeliveryCalculationResponse(BaseModel):
    """Модель для ответа с результатом расчета стоимости доставки."""
    price: float = Field(..., description="Стоимость доставки")
    price_base: float = Field(..., description="Базовая стоимость доставки")
    price_service: float = Field(..., description="Стоимость дополнительных услуг")
    delivery_period: int = Field(..., description="Срок доставки в днях")

# Модель товара для расчета доставки из корзины
class CartItemModel(BaseModel):
    """Модель товара в корзине для расчета доставки."""
    product_id: int = Field(..., description="ID товара")
    quantity: int = Field(..., description="Количество товара")
    weight: Optional[float] = Field(None, description="Вес товара в граммах")
    height: Optional[int] = Field(None, description="Высота товара в сантиметрах")
    width: Optional[int] = Field(None, description="Ширина товара в сантиметрах")
    depth: Optional[int] = Field(None, description="Глубина товара в сантиметрах")
    price: float = Field(..., description="Цена товара")

# Модель для запроса расчета доставки из корзины
class CartDeliveryRequest(BaseModel):
    """Модель для запроса расчета стоимости доставки из корзины."""
    items: List[CartItemModel] = Field(..., description="Список товаров в корзине")
    pvz_code: Optional[str] = Field(None, description="Код ПВЗ (если доставка до ПВЗ)")
    zip_code: Optional[str] = Field(None, description="Почтовый индекс для курьерской доставки")
    city_name: Optional[str] = Field(None, description="Название города для курьерской доставки")
    delivery_type: str = Field(..., description="Тип доставки (boxberry_pickup_point или boxberry_courier)")
    is_payment_on_delivery: bool = Field(True, description="Оплата при получении (True) или на сайте (False)")