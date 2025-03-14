from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, CheckConstraint, DateTime, Boolean, Text, func, select, Enum
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import selectinload
import enum

class Base(DeclarativeBase):
    pass

class OrderStatusEnum(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"

class PaymentMethodEnum(enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cash_on_delivery"

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
        except Exception as e:
            print(f"Ошибка при получении статусов заказов: {str(e)}")
            return []
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, status_id: int) -> Optional["OrderStatusModel"]:
        """Получить статус заказа по ID"""
        try:
            result = await session.get(cls, status_id)
            return result
        except Exception as e:
            print(f"Ошибка при получении статуса заказа: {str(e)}")
            return None
    
    @classmethod
    async def get_default(cls, session: AsyncSession) -> Optional["OrderStatusModel"]:
        """Получить статус заказа по умолчанию (с наименьшим sort_order)"""
        try:
            query = select(cls).order_by(cls.sort_order.asc()).limit(1)
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
            print(f"Ошибка при получении статуса заказа по умолчанию: {str(e)}")
            return None

class OrderModel(Base):
    """Модель заказа"""
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status_id: Mapped[int] = mapped_column(ForeignKey("order_statuses.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_method: Mapped[PaymentMethodEnum] = mapped_column(Enum(PaymentMethodEnum), nullable=False, default=PaymentMethodEnum.CASH_ON_DELIVERY)
    
    # Связь с элементами заказа
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    
    # Связь со статусом заказа
    status = relationship("OrderStatusModel", back_populates="orders")
    
    # История изменений статуса
    status_history = relationship("OrderStatusHistoryModel", back_populates="order", cascade="all, delete-orphan")
    
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
                selectinload(cls.status_history)
            ).filter(cls.id == order_id)
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
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
                selectinload(cls.status)
            ).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            items = result.scalars().all()
            
            return items, total
        except Exception as e:
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
        order_by: str = "created_at",
        order_dir: str = "desc"
    ) -> Tuple[List["OrderModel"], int]:
        """Получить все заказы с пагинацией и фильтрацией"""
        try:
            # Формируем базовый запрос
            query = select(cls)
            count_query = select(func.count()).select_from(cls)
            
            # Применяем фильтры
            filters = []
            if status_id is not None:
                filters.append(cls.status_id == status_id)
            if user_id is not None:
                filters.append(cls.user_id == user_id)
            
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
                selectinload(cls.status)
            ).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            items = result.scalars().all()
            
            return items, total
        except Exception as e:
            print(f"Ошибка при получении всех заказов: {str(e)}")
            return [], 0

class OrderItemModel(Base):
    """Модель элемента заказа"""
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
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)  # Общая цена (quantity * product_price)
    
    # Связь с заказом
    order = relationship("OrderModel", back_populates="items")

class OrderStatusHistoryModel(Base):
    """Модель истории изменения статуса заказа"""
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
    """Модель адреса доставки"""
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
    """Модель адреса для выставления счета"""
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