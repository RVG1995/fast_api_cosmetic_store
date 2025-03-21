from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, CheckConstraint, DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Tuple
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
            
    @classmethod
    async def get_user_carts(
        cls, 
        session: AsyncSession, 
        page: int = 1, 
        limit: int = 10,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        user_id: Optional[int] = None,
        filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List["CartModel"], int]:
        """
        Получить список корзин пользователей (не анонимных) с пагинацией
        
        Args:
            session: Асинхронная сессия SQLAlchemy
            page: Номер страницы (начиная с 1)
            limit: Количество записей на странице
            sort_by: Поле для сортировки (id, user_id, created_at, updated_at)
            sort_order: Порядок сортировки (asc, desc)
            user_id: Опциональный фильтр по ID пользователя
            filter: Опциональный фильтр (with_items/empty)
            search: Опциональный поиск по ID корзины или ID пользователя
            
        Returns:
            Кортеж (список корзин, общее количество)
        """
        try:
            # Основной запрос с фильтрацией только пользовательских корзин
            query = select(cls).options(
                selectinload(cls.items)
            ).filter(
                cls.user_id != None  # только корзины с user_id (не анонимные)
            )
            
            # Если указан фильтр по user_id, добавляем его
            if user_id is not None:
                query = query.filter(cls.user_id == user_id)
            
            # Применяем фильтр
            if filter == "with_items":
                # Фильтрация корзин с товарами
                subquery = select(CartItemModel.cart_id).distinct()
                query = query.filter(cls.id.in_(subquery))
            elif filter == "empty":
                # Фильтрация пустых корзин
                subquery = select(CartItemModel.cart_id).distinct()
                query = query.filter(cls.id.not_in(subquery))
            
            # Добавляем поиск, если указан
            if search:
                # Поиск по ID корзины (преобразуем строку в число)
                try:
                    search_id = int(search)
                    query = query.filter(cls.id == search_id)
                except ValueError:
                    # Если не получается преобразовать в число, игнорируем поиск
                    pass
            
            # Добавляем сортировку
            if sort_by == "id":
                query = query.order_by(cls.id.desc() if sort_order == "desc" else cls.id.asc())
            elif sort_by == "user_id":
                query = query.order_by(cls.user_id.desc() if sort_order == "desc" else cls.user_id.asc())
            elif sort_by == "created_at":
                query = query.order_by(cls.created_at.desc() if sort_order == "desc" else cls.created_at.asc())
            else:  # default: updated_at
                query = query.order_by(cls.updated_at.desc() if sort_order == "desc" else cls.updated_at.asc())
                
            # Выполняем запрос для подсчета общего количества корзин
            count_query = select(func.count()).select_from(
                select(cls).filter(cls.user_id != None).subquery()
            )
            
            # Если указан фильтр по user_id, добавляем его и в запрос подсчета
            if user_id is not None:
                count_query = select(func.count()).select_from(
                    select(cls).filter(cls.user_id != None, cls.user_id == user_id).subquery()
                )
                
            count_result = await session.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # Добавляем пагинацию
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)
            
            # Выполняем основной запрос
            result = await session.execute(query)
            carts = result.scalars().all()
            
            return carts, total_count
            
        except Exception as e:
            # Логируем ошибку и возвращаем пустой список
            print(f"Ошибка при получении списка корзин пользователей: {str(e)}")
            return [], 0

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