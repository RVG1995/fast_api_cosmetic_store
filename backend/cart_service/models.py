from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, CheckConstraint, DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import selectinload

class Base(DeclarativeBase):
    pass

class CartModel(Base):
    """Модель корзины пользователя"""
    __tablename__ = 'carts'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # Может быть NULL для неавторизованных пользователей
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # Для неавторизованных пользователей
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связь с элементами корзины
    items = relationship("CartItemModel", back_populates="cart", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Ограничение: либо user_id, либо session_id должны быть указаны
        CheckConstraint('(user_id IS NOT NULL) OR (session_id IS NOT NULL)', 
                        name='check_user_or_session'),
    )
    
    @classmethod
    async def get_user_cart(cls, session: AsyncSession, user_id: int) -> Optional["CartModel"]:
        """Получить корзину по ID пользователя"""
        try:
            query = select(cls).options(
                selectinload(cls.items)
            ).filter(cls.user_id == user_id)
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Логируем ошибку и возвращаем None
            print(f"Ошибка при получении корзины пользователя: {str(e)}")
            return None
    
    @classmethod
    async def get_session_cart(cls, session: AsyncSession, session_id: str) -> Optional["CartModel"]:
        """Получить корзину по ID сессии (для неавторизованных пользователей)"""
        try:
            query = select(cls).options(
                selectinload(cls.items)
            ).filter(cls.session_id == session_id)
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Логируем ошибку и возвращаем None
            print(f"Ошибка при получении корзины сессии: {str(e)}")
            return None

class CartItemModel(Base):
    """Модель элемента корзины"""
    __tablename__ = 'cart_items'
    __table_args__ = (
        CheckConstraint('quantity > 0', name='cart_item_quantity_positive'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связь с корзиной
    cart = relationship("CartModel", back_populates="items")
    
    @classmethod
    async def get_item_by_product(cls, session: AsyncSession, cart_id: int, product_id: int) -> Optional["CartItemModel"]:
        """Получить элемент корзины по ID продукта и ID корзины"""
        try:
            query = select(cls).filter(cls.cart_id == cart_id, cls.product_id == product_id)
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Логируем ошибку и возвращаем None
            print(f"Ошибка при получении элемента корзины: {str(e)}")
            return None 