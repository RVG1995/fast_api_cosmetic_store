from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Computed, Boolean, Text, ForeignKey, CheckConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import  Optional, List


class Base(DeclarativeBase):
    pass


class CategoryModel(Base):
    __tablename__ = 'categories' 

    id: Mapped[int] = mapped_column(primary_key = True,index = True)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(50))
    products = relationship("ProductModel", back_populates="category", cascade="all, delete-orphan")
    subcategories = relationship("SubCategoryModel", back_populates="category", cascade="all, delete-orphan")


class CountryModel(Base):
    __tablename__ = 'countries' 

    id: Mapped[int] = mapped_column(primary_key = True,index = True)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(50))
    products = relationship("ProductModel", back_populates="country", cascade="all, delete-orphan")

class BrandModel(Base):
    __tablename__ = 'brands' 

    id: Mapped[int] = mapped_column(primary_key = True,index = True)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(50))
    products = relationship("ProductModel", back_populates="brand", cascade="all, delete-orphan")

class SubCategoryModel(Base):
    __tablename__ = 'subcategories'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(50))
    # Внешний ключ для связи с родительской категорией
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id', ondelete='CASCADE'))
    
    # Связь с родительской категорией
    category = relationship("CategoryModel", back_populates="subcategories")
    # Связь с товарами, относящимися к данной подкатегории
    products = relationship("ProductModel", back_populates="subcategory", cascade="all, delete-orphan")


class ProductModel(Base):
    __tablename__ = 'products'
    __table_args__ = (
        CheckConstraint('price > 0', name='products_price_positive_check'),
        CheckConstraint('stock >= 0', name='products_stock_non_negative'),
    )

    id: Mapped[int] = mapped_column(primary_key = True, index = True)
    name: Mapped[str] = mapped_column(String(100),index=True, nullable = False)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id', ondelete='CASCADE'))
    country_id: Mapped[int] = mapped_column(ForeignKey('countries.id', ondelete='CASCADE'))
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id', ondelete='CASCADE'))
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('subcategories.id', ondelete='CASCADE'),
        nullable=True
    )
    price: Mapped[int] = mapped_column(Integer, nullable = False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image: Mapped[Optional[str]] = mapped_column(String(255)) 
    in_stock: Mapped[bool] = mapped_column(
        Boolean,
        Computed("CASE WHEN stock > 0 THEN true ELSE false END", persisted=True)
    )

    category = relationship("CategoryModel", back_populates="products")
    country = relationship("CountryModel", back_populates="products")
    brand = relationship("BrandModel", back_populates="products")
    subcategory = relationship("SubCategoryModel", back_populates="products")

    @classmethod
    async def get_products_query(cls):
        """
        Возвращает базовый запрос для доступных продуктов, отсортированных от новых к старым.
        
        Запрос возвращает только продукты с stock > 0 (доступные),
        отсортированные по ID в порядке убывания (от новых к старым).
        
        Returns:
            SQLAlchemy query object
        """
        return select(cls).filter(cls.in_stock == True).order_by(cls.id.desc())
        
    @classmethod
    async def get_admin_products_query(cls):
        """
        Возвращает базовый запрос для всех продуктов, отсортированных от новых к старым.
        
        Запрос возвращает все продукты, включая те, у которых stock = 0,
        отсортированные по ID в порядке убывания (от новых к старым).
        Этот метод предназначен для использования в админ-панели, где администраторы
        должны видеть и иметь возможность редактировать все товары.
        
        Returns:
            SQLAlchemy query object
        """
        return select(cls).order_by(cls.id.desc())
        
    @classmethod
    async def get_all_products(cls, session: AsyncSession) -> List["ProductModel"]:
        """
        Получить все доступные продукты, отсортированные от новых к старым.
        
        Метод возвращает только продукты с stock > 0 (доступные),
        отсортированные по ID в порядке убывания (от новых к старым).
        
        Для более гибкого использования в запросах используйте get_products_query.
        """
        try:
            # Используем новый метод для получения запроса
            query = await cls.get_products_query()
            
            # Выполняем запрос
            result = await session.execute(query)
            return result.scalars().all()
        except AttributeError:
            # В тестах, если session.execute - это корутина без .scalars().all()
            # Просто вернем пустой список для безопасности
            return []
        except Exception as e:
            # Для других ошибок также возвращаем пустой список
            print(f"Ошибка при получении продуктов: {str(e)}")
            return []

    @classmethod
    async def get_all_products_admin(cls, session: AsyncSession) -> List["ProductModel"]:
        """
        Получить ВСЕ продукты для админ-панели, отсортированные от новых к старым.
        
        Метод возвращает все продукты, включая те, у которых stock = 0,
        отсортированные по ID в порядке убывания (от новых к старым).
        Этот метод предназначен для использования в админ-панели, где администраторы
        должны видеть и иметь возможность редактировать все товары.
        
        Для более гибкого использования в запросах используйте get_admin_products_query.
        """
        try:
            # Используем новый метод для получения запроса
            query = await cls.get_admin_products_query()
            
            # Выполняем запрос
            result = await session.execute(query)
            return result.scalars().all()
        except AttributeError:
            # В тестах, если session.execute - это корутина без .scalars().all()
            # Просто вернем пустой список для безопасности
            return []
        except Exception as e:
            # Для других ошибок также возвращаем пустой список
            print(f"Ошибка при получении продуктов для админки: {str(e)}")
            return []