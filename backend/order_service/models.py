"""Модели для сервиса заказов."""

import enum
import logging
from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, Float, String, ForeignKey, CheckConstraint, DateTime, Boolean, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass

class OrderStatusEnum(enum.Enum):
    """Перечисление статусов заказа."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"

class OrderStatusModel(Base):
    """Модель статуса заказа"""
    __tablename__ = 'order_statuses'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#808080")  # Цвет для отображения статуса
    allow_cancel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # Разрешение на отмену заказа
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # Является ли статус финальным
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Порядок сортировки
    
    # Связь с заказами
    orders = relationship("OrderModel", back_populates="status")
    
    @classmethod
    async def get_all(cls, session: AsyncSession) -> List["OrderStatusModel"]:
        """Получить все статусы заказов, отсортированные по порядку сортировки"""
        try:
            query = select(cls).order_by(cls.sort_order.asc())
            result = await session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            print(f"Ошибка при получении статусов заказов: {str(e)}")
            return []
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, status_id: int) -> Optional["OrderStatusModel"]:
        """Получить статус заказа по ID"""
        try:
            result = await session.get(cls, status_id)
            return result
        except SQLAlchemyError as e:
            print(f"Ошибка при получении статуса заказа: {str(e)}")
            return None
    
    @classmethod
    async def get_default(cls, session: AsyncSession) -> Optional["OrderStatusModel"]:
        """Получить статус заказа по умолчанию (с наименьшим sort_order)"""
        try:
            query = select(cls).order_by(cls.sort_order.asc()).limit(1)
            result = await session.execute(query)
            return result.scalars().first()
        except SQLAlchemyError as e:
            print(f"Ошибка при получении статуса заказа по умолчанию: {str(e)}")
            return None


class DeliveryInfoModel(Base):
    """Модель информации о доставке."""
    __tablename__ = 'delivery_info'

    __table_args__ = (
        CheckConstraint('delivery_cost > 0', name='delivery_cost_positive'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(50), nullable=False)  # boxberry_pickup_point, boxberry_courier, cdek_pickup_point, cdek_courier
    boxberry_point_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID пункта выдачи
    boxberry_point_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Адрес пункта выдачи
    delivery_cost: Mapped[float] = mapped_column(Float, nullable=False)  # Стоимость доставки
    tracking_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Номер отслеживания
    label_url_boxberry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # URL на этикетку Boxberry
    status_in_delivery_service: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Статус в доставке
    
    # Добавляем обратное отношение к OrderModel
    order = relationship("OrderModel", back_populates="delivery_info")

class OrderModel(Base):
    """Модель заказа."""
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # Может быть null для анонимных пользователей
    status_id: Mapped[int] = mapped_column(ForeignKey("order_statuses.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Новое поле для связи с промокодом
    promo_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("promo_codes.id", ondelete="SET NULL"), nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0)  # Сумма скидки
    
    # Данные о клиенте и доставке
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    delivery_address: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Изменяем на отношение один-к-одному, добавляя uselist=False
    delivery_info = relationship("DeliveryInfoModel", back_populates="order", cascade="all, delete-orphan", uselist=False)
    
    # Информация о способе оплаты
    is_payment_on_delivery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # Оплата при получении
    
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Связь с элементами заказа
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    
    # Связь со статусом заказа
    status = relationship("OrderStatusModel", back_populates="orders")
    
    # История изменений статуса
    status_history = relationship("OrderStatusHistoryModel", back_populates="order", cascade="all, delete-orphan")
    
    # Связь с промокодом
    promo_code = relationship("PromoCodeModel", back_populates="orders")

    receive_notifications: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    
    personal_data_agreement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    @property
    def order_number(self) -> str:
        """Получить номер заказа в формате ID + год"""
        year = self.created_at.year
        return f"{self.id}-{year}"
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, order_id: int) -> Optional["OrderModel"]:
        """Получить заказ по ID с загрузкой элементов и статуса"""
        try:
            query = select(cls).options(
                selectinload(cls.items),
                selectinload(cls.status),
                selectinload(cls.status_history),
                selectinload(cls.delivery_info)
            ).filter(cls.id == order_id)
            result = await session.execute(query)
            return result.scalars().first()
        except SQLAlchemyError as e:
            print(f"Ошибка при получении заказа: {str(e)}")
            return None
    
    @classmethod
    async def get_by_user(
        cls, 
        session: AsyncSession, 
        user_id: int,
        page: int = 1, 
        limit: int = 10,
        status_id: Optional[int] = None
    ) -> Tuple[List["OrderModel"], int]:
        """Получить заказы пользователя с пагинацией"""
        try:
            # Формируем базовый запрос
            query = select(cls).filter(cls.user_id == user_id)
            count_query = select(func.count()).select_from(select(cls).filter(cls.user_id == user_id).subquery())
            
            # Фильтрация по статусу, если указан
            if status_id is not None:
                query = query.filter(cls.status_id == status_id)
                count_query = select(func.count()).select_from(
                    select(cls).filter(cls.user_id == user_id, cls.status_id == status_id).subquery()
                )
            
            # Добавляем сортировку
            query = query.order_by(cls.created_at.desc())
            
            # Вычисляем общее количество
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            
            # Добавляем пагинацию
            offset = (page - 1) * limit
            query = query.options(
                selectinload(cls.items),
                selectinload(cls.status),
                selectinload(cls.delivery_info)
            ).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            items = result.scalars().all()
            
            return items, total
        except SQLAlchemyError as e:
            print(f"Ошибка при получении заказов пользователя: {str(e)}")
            return [], 0
    
    @classmethod
    async def get_all(
        cls, 
        session: AsyncSession, 
        page: int = 1, 
        limit: int = 10,
        status_id: Optional[int] = None,
        user_id: Optional[int] = None,
        id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
        username: Optional[str] = None
    ) -> Tuple[List["OrderModel"], int]:
        """Получить все заказы с пагинацией и фильтрацией"""
        try:
            # Логируем входящие параметры фильтрации
            logger = logging.getLogger("order_model")
            logger.info("Запрос всех заказов с параметрами: page=%s, limit=%s, status_id=%s, user_id=%s, id=%s, date_from=%s, date_to=%s, username=%s",
                       page, limit, status_id, user_id, id, date_from, date_to, username)
            
            # Формируем базовый запрос
            query = select(cls)
            count_query = select(func.count()).select_from(cls)
            
            # Применяем фильтры
            filters = []
            if status_id is not None:
                filters.append(cls.status_id == status_id)
            if user_id is not None:
                filters.append(cls.user_id == user_id)
            if id is not None:
                filters.append(cls.id == id)
            
            # Добавляем фильтрацию по имени пользователя
            if username is not None and username.strip():
                # Используем оператор ILIKE для регистронезависимого поиска по части имени
                # Обратите внимание, что % нужно добавить и в начало, и в конец для поиска по подстроке
                filters.append(cls.full_name.ilike(f'%{username}%'))
                logger.info("Применяется фильтр по имени пользователя: full_name ILIKE %%%s%%", username)
                logger.debug("Текущие фильтры: %s", filters)
            
            # Добавляем фильтрацию по датам
            if date_from is not None:
                try:
                    # Создаем объект datetime для начала дня
                    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
                    filters.append(cls.created_at >= date_from_obj)
                    logger.info("Применяется фильтр по начальной дате: created_at >= %s", date_from_obj)
                except ValueError as e:
                    logger.error("Ошибка при обработке date_from=%s: %s", date_from, str(e))
            
            if date_to is not None:
                try:
                    # Создаем объект datetime для конца дня
                    date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                    filters.append(cls.created_at <= date_to_obj)
                    logger.info("Применяется фильтр по конечной дате: created_at <= %s", date_to_obj)
                except ValueError as e:
                    logger.error("Ошибка при обработке date_to=%s: %s", date_to, str(e))
            
            if filters:
                query = query.filter(*filters)
                count_query = select(func.count()).select_from(select(cls).filter(*filters).subquery())
            
            # Добавляем сортировку
            if order_by == "id":
                query = query.order_by(cls.id.desc() if order_dir == "desc" else cls.id.asc())
            elif order_by == "user_id":
                query = query.order_by(cls.user_id.desc() if order_dir == "desc" else cls.user_id.asc())
            elif order_by == "total_price":
                query = query.order_by(cls.total_price.desc() if order_dir == "desc" else cls.total_price.asc())
            elif order_by == "updated_at":
                query = query.order_by(cls.updated_at.desc() if order_dir == "desc" else cls.updated_at.asc())
            else:  # по умолчанию created_at
                query = query.order_by(cls.created_at.desc() if order_dir == "desc" else cls.created_at.asc())
            
            # Вычисляем общее количество
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            
            # Добавляем пагинацию
            offset = (page - 1) * limit
            query = query.options(
                selectinload(cls.items),
                selectinload(cls.status),
                selectinload(cls.delivery_info)
            ).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            items = result.scalars().all()
            
            return items, total
        except SQLAlchemyError as e:
            logger = logging.getLogger("order_model")
            logger.error("Ошибка при получении всех заказов: %s", str(e))
            return [], 0

class OrderItemModel(Base):
    """Модель элемента заказа."""
    __tablename__ = 'order_items'
    __table_args__ = (
        CheckConstraint('quantity > 0', name='order_item_quantity_positive'),
        CheckConstraint('product_price >= 0', name='order_item_price_non_negative'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Название товара на момент заказа
    product_price: Mapped[int] = mapped_column(Integer, nullable=False)  # Цена товара на момент заказа
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)  # Общая цена (quantity * product_price)
    
    # Связь с заказом
    order = relationship("OrderModel", back_populates="items")

class OrderStatusHistoryModel(Base):
    """Модель истории изменения статуса заказа."""
    __tablename__ = 'order_status_history'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status_id: Mapped[int] = mapped_column(ForeignKey("order_statuses.id", ondelete="RESTRICT"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    changed_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID пользователя, изменившего статус
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Примечания к изменению статуса
    
    # Связи
    order = relationship("OrderModel", back_populates="status_history")
    status = relationship("OrderStatusModel")
    
    @classmethod
    async def add_status_change(
        cls, 
        session: AsyncSession, 
        order_id: int, 
        status_id: int, 
        changed_by_user_id: Optional[int] = None, 
        notes: Optional[str] = None
    ) -> "OrderStatusHistoryModel":
        """Добавить запись об изменении статуса заказа"""
        history_record = cls(
            order_id=order_id,
            status_id=status_id,
            changed_by_user_id=changed_by_user_id,
            notes=notes
        )
        session.add(history_record)
        await session.flush()  # Записываем данные, но не коммитим
        return history_record

class ShippingAddressModel(Base):
    """Модель адреса доставки."""
    __tablename__ = 'shipping_addresses'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

class BillingAddressModel(Base):
    """Модель адреса для выставления счета."""
    __tablename__ = 'billing_addresses'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

class PaymentStatusModel(Base):
    """Модель статуса оплаты заказа."""
    __tablename__ = "payment_statuses"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#3498db")
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=func.now())
    
    # Обратные отношения (если будут связи)
    # orders = relationship("OrderModel", back_populates="payment_status")
    
    @classmethod
    async def get_all(cls, session: AsyncSession, skip: int = 0, limit: int = 100) -> List["PaymentStatusModel"]:
        """Получение всех статусов оплаты"""
        query = select(cls).offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, status_id: int) -> Optional["PaymentStatusModel"]:
        """Получение статуса по ID"""
        query = select(cls).where(cls.id == status_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_name(cls, session: AsyncSession, name: str) -> Optional["PaymentStatusModel"]:
        """Получение статуса по названию"""
        query = select(cls).where(cls.name == name)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def create(cls, session: AsyncSession, status_data) -> "PaymentStatusModel":
        """Создание нового статуса оплаты"""
        db_status = cls(**status_data.model_dump())
        session.add(db_status)
        await session.commit()
        await session.refresh(db_status)
        return db_status
    
    @classmethod
    async def update(cls, session: AsyncSession, status_id: int, status_data) -> Optional["PaymentStatusModel"]:
        """Обновление статуса оплаты"""
        db_status = await cls.get_by_id(session, status_id)
        if not db_status:
            return None
        
        data_dict = status_data.model_dump(exclude_unset=True)
        for key, value in data_dict.items():
            setattr(db_status, key, value)
        
        await session.commit()
        await session.refresh(db_status)
        return db_status
    
    @classmethod
    async def delete(cls, session: AsyncSession, status_id: int) -> bool:
        """Удаление статуса оплаты"""
        db_status = await cls.get_by_id(session, status_id)
        if not db_status:
            return False
        
        await session.delete(db_status)
        await session.commit()
        return True
    
    @classmethod
    async def is_used_in_orders(cls, session: AsyncSession, status_id: int) -> bool:
        """Проверка, используется ли статус в заказах
        
        Проверяет наличие заказов с соответствующим статусом оплаты (is_paid).
        Этот метод позволяет предотвратить удаление статусов, которые используются в заказах.
        """
        try:
            # Получаем статус оплаты
            payment_status = await cls.get_by_id(session, status_id)
            if not payment_status:
                return False
                
            # Проверяем наличие заказов, соответствующих статусу оплаты
            # Если статус оплаты имеет is_paid=True, ищем заказы с is_paid=True
            # Если статус оплаты имеет is_paid=False, ищем заказы с is_paid=False
            # Используем exists() и limit(1) для оптимизации запроса - нам важен только факт наличия
            query = select(OrderModel.id).where(
                OrderModel.is_paid == payment_status.is_paid
            ).limit(1)
            
            result = await session.execute(query)
            return result.first() is not None
        except SQLAlchemyError as e:
            logging.error("Ошибка при проверке использования статуса оплаты: %s", str(e))
            return False

class PromoCodeModel(Base):
    """Модель промокода."""
    __tablename__ = 'promo_codes'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    discount_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Связь с заказами
    orders = relationship("OrderModel", back_populates="promo_code")
    
    # Связь с использованными промокодами
    usages = relationship("PromoCodeUsageModel", back_populates="promo_code", cascade="all, delete-orphan")
    
    @property
    def is_valid(self) -> bool:
        """Проверяет, действителен ли промокод (по сроку действия)"""
        return self.is_active and self.valid_until >= datetime.now()
    
    @classmethod
    async def get_by_code(cls, session: AsyncSession, code: str) -> Optional["PromoCodeModel"]:
        """Получить промокод по его коду."""
        try:
            query = select(cls).filter(cls.code == code)
            result = await session.execute(query)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logging.error("Ошибка при получении промокода: %s", str(e))
            return None
    
    @classmethod
    async def get_all(cls, session: AsyncSession, skip: int = 0, limit: int = 100) -> List["PromoCodeModel"]:
        """Получить все промокоды с пагинацией."""
        try:
            query = select(cls).order_by(cls.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logging.error("Ошибка при получении промокодов: %s", str(e))
            return []
    
    @classmethod
    async def get_active(cls, session: AsyncSession) -> List["PromoCodeModel"]:
        """Получить все активные промокоды."""
        try:
            query = select(cls).filter(
                cls.is_active == True,
                cls.valid_until >= datetime.now()
            ).order_by(cls.created_at.desc())
            result = await session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logging.error("Ошибка при получении активных промокодов: %s", str(e))
            return []

class PromoCodeUsageModel(Base):
    """Модель использования промокода."""
    __tablename__ = 'promo_code_usages'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    promo_code_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    
    # Связь с промокодом
    promo_code = relationship("PromoCodeModel", back_populates="usages")
    
    @classmethod
    async def check_usage(cls, session: AsyncSession, promo_code_id: int, email: str, phone: str) -> bool:
        """Проверить, использовал ли пользователь промокод ранее (по email и телефону)"""
        try:
            query = select(cls).filter(
                cls.promo_code_id == promo_code_id,
                (cls.email == email) | (cls.phone == phone)
            )
            result = await session.execute(query)
            return result.scalars().first() is not None
        except SQLAlchemyError as e:
            logging.error("Ошибка при проверке использования промокода: %s", str(e))
            return False
