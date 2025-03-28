from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, CheckConstraint, DateTime, Boolean, Text, func, select, Enum, Float
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import selectinload
import enum
import logging

# Настройка логирования
logger = logging.getLogger("review_service")

class Base(DeclarativeBase):
    pass

class ReviewTypeEnum(enum.Enum):
    PRODUCT = "product"
    STORE = "store"

class ReviewModel(Base):
    """Модель отзыва (как для товаров, так и для магазина)"""
    __tablename__ = 'reviews'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Дополнительные данные о пользователе
    user_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_email: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Дополнительные данные о товаре, если тип отзыва = product
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Связь с комментариями администратора
    admin_comments = relationship("AdminCommentModel", back_populates="review", cascade="all, delete-orphan")
    
    # Связь с лайками/дизлайками
    reactions = relationship("ReviewReactionModel", back_populates="review", cascade="all, delete-orphan")
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, review_id: int) -> Optional["ReviewModel"]:
        """Получение отзыва по ID"""
        try:
            query = select(cls).where(cls.id == review_id).options(
                selectinload(cls.admin_comments),
                selectinload(cls.reactions)
            )
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Ошибка при получении отзыва по ID {review_id}: {str(e)}")
            return None
    
    @classmethod
    async def get_by_product_id(
        cls, 
        session: AsyncSession, 
        product_id: int,
        page: int = 1,
        limit: int = 10,
        include_hidden: bool = False
    ) -> Tuple[List["ReviewModel"], int]:
        """Получение отзывов для товара с пагинацией"""
        try:
            # Базовый запрос для отзывов товара
            query = select(cls).where(
                cls.review_type == ReviewTypeEnum.PRODUCT.value,
                cls.product_id == product_id
            )
            
            # Запрос для подсчета общего количества
            count_query = select(func.count()).where(
                cls.review_type == ReviewTypeEnum.PRODUCT.value,
                cls.product_id == product_id
            )
            
            # Фильтрация по видимости, если нужно показывать только видимые отзывы
            if not include_hidden:
                query = query.where(cls.is_hidden == False)
                count_query = count_query.where(cls.is_hidden == False)
            
            # Подсчет общего количества отзывов
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            
            # Логируем информацию
            logger.info(f"Найдено {total} отзывов для товара {product_id} (include_hidden={include_hidden})")
            
            # Добавляем сортировку, пагинацию и подгрузку связанных данных
            offset = (page - 1) * limit
            query = query.options(
                selectinload(cls.admin_comments),
                selectinload(cls.reactions)
            ).order_by(cls.created_at.desc()).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            reviews = result.scalars().all()
            
            # Логируем результат
            logger.info(f"Получено {len(reviews)} отзывов для товара {product_id}")
            
            return reviews, total
        except Exception as e:
            logger.error(f"Ошибка при получении отзывов для товара {product_id}: {str(e)}")
            return [], 0
    
    @classmethod
    async def get_store_reviews(
        cls, 
        session: AsyncSession, 
        page: int = 1,
        limit: int = 10,
        include_hidden: bool = False
    ) -> Tuple[List["ReviewModel"], int]:
        """Получение отзывов для магазина с пагинацией"""
        try:
            # Базовый запрос для отзывов магазина
            query = select(cls).where(
                cls.review_type == ReviewTypeEnum.STORE.value
            )
            
            # Запрос для подсчета общего количества
            count_query = select(func.count()).where(
                cls.review_type == ReviewTypeEnum.STORE.value
            )
            
            # Фильтрация по видимости, если нужно показывать только видимые отзывы
            if not include_hidden:
                query = query.where(cls.is_hidden == False)
                count_query = count_query.where(cls.is_hidden == False)
            
            # Подсчет общего количества отзывов
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            
            # Логируем информацию
            logger.info(f"Найдено {total} отзывов для магазина (include_hidden={include_hidden})")
            
            # Добавляем сортировку, пагинацию и подгрузку связанных данных
            offset = (page - 1) * limit
            query = query.options(
                selectinload(cls.admin_comments),
                selectinload(cls.reactions)
            ).order_by(cls.created_at.desc()).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            reviews = result.scalars().all()
            
            # Логируем результат
            logger.info(f"Получено {len(reviews)} отзывов для магазина")
            
            return reviews, total
        except Exception as e:
            logger.error(f"Ошибка при получении отзывов для магазина: {str(e)}")
            return [], 0
    
    @classmethod
    async def get_user_reviews(
        cls, 
        session: AsyncSession, 
        user_id: int,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List["ReviewModel"], int]:
        """Получение отзывов пользователя с пагинацией"""
        try:
            # Базовый запрос для отзывов пользователя
            query = select(cls).where(cls.user_id == user_id)
            
            # Запрос для подсчета общего количества
            count_query = select(func.count()).where(cls.user_id == user_id)
            
            # Подсчет общего количества отзывов
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0
            
            # Добавляем сортировку, пагинацию и подгрузку связанных данных
            offset = (page - 1) * limit
            query = query.options(
                selectinload(cls.admin_comments),
                selectinload(cls.reactions)
            ).order_by(cls.created_at.desc()).offset(offset).limit(limit)
            
            # Выполняем запрос
            result = await session.execute(query)
            reviews = result.scalars().all()
            
            return reviews, total
        except Exception as e:
            logger.error(f"Ошибка при получении отзывов пользователя {user_id}: {str(e)}")
            return [], 0
    
    @classmethod
    async def get_product_avg_rating(cls, session: AsyncSession, product_id: int) -> float:
        """Получение среднего рейтинга товара"""
        try:
            query = select(func.avg(cls.rating)).where(
                cls.review_type == ReviewTypeEnum.PRODUCT.value,
                cls.product_id == product_id,
                cls.is_hidden == False
            )
            result = await session.execute(query)
            avg_rating = result.scalar() or 0.0
            return float(avg_rating)
        except Exception as e:
            logger.error(f"Ошибка при получении среднего рейтинга товара {product_id}: {str(e)}")
            return 0.0
    
    @classmethod
    async def get_store_avg_rating(cls, session: AsyncSession) -> float:
        """Получение среднего рейтинга магазина"""
        try:
            query = select(func.avg(cls.rating)).where(
                cls.review_type == ReviewTypeEnum.STORE.value,
                cls.is_hidden == False
            )
            result = await session.execute(query)
            avg_rating = result.scalar() or 0.0
            return float(avg_rating)
        except Exception as e:
            logger.error(f"Ошибка при получении среднего рейтинга магазина: {str(e)}")
            return 0.0
    
    @classmethod
    async def check_user_can_review_product(cls, session: AsyncSession, user_id: int, product_id: int) -> bool:
        """
        Проверка, может ли пользователь оставить отзыв на товар
        (заказал и товар доставлен)
        """
        from services import order_api
        
        try:
            return await order_api.check_user_can_review_product(user_id, product_id)
        except Exception as e:
            logger.error(f"Ошибка при проверке возможности оставить отзыв на товар {product_id} пользователем {user_id}: {str(e)}")
            return False
    
    @classmethod
    async def check_user_can_review_store(cls, session: AsyncSession, user_id: int) -> bool:
        """
        Проверка, может ли пользователь оставить отзыв на магазин
        (имеет хотя бы один доставленный заказ)
        """
        from services import order_api
        
        try:
            return await order_api.check_user_can_review_store(user_id)
        except Exception as e:
            logger.error(f"Ошибка при проверке возможности оставить отзыв на магазин пользователем {user_id}: {str(e)}")
            return False
    
    def get_reaction_stats(self) -> Dict[str, int]:
        """Получение статистики по лайкам/дизлайкам"""
        likes = 0
        dislikes = 0
        
        # Проверяем, есть ли загруженные реакции
        if hasattr(self, 'reactions') and self.reactions is not None:
            for reaction in self.reactions:
                if reaction.reaction_type == ReactionTypeEnum.LIKE.value:
                    likes += 1
                elif reaction.reaction_type == ReactionTypeEnum.DISLIKE.value:
                    dislikes += 1
            
            logger.info(f"Подсчитаны реакции для отзыва {self.id}: likes={likes}, dislikes={dislikes}")
        else:
            logger.warning(f"У отзыва {self.id} не загружены реакции, статистика может быть неточной")
        
        return {
            "likes": likes,
            "dislikes": dislikes
        }


class AdminCommentModel(Base):
    """Модель комментария администратора к отзыву"""
    __tablename__ = 'admin_comments'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    admin_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Дополнительные данные об администраторе
    admin_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Обратная связь с отзывом
    review = relationship("ReviewModel", back_populates="admin_comments")
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, comment_id: int) -> Optional["AdminCommentModel"]:
        """Получение комментария по ID"""
        try:
            return await session.get(cls, comment_id)
        except Exception as e:
            logger.error(f"Ошибка при получении комментария по ID {comment_id}: {str(e)}")
            return None


class ReactionTypeEnum(enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class ReviewReactionModel(Base):
    """Модель реакции (лайк/дизлайк) на отзыв"""
    __tablename__ = 'review_reactions'
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    
    # Обратная связь с отзывом
    review = relationship("ReviewModel", back_populates="reactions")
    
    # Составной уникальный индекс, чтобы пользователь мог оставить только одну реакцию на отзыв
    __table_args__ = (
        CheckConstraint(
            "reaction_type IN ('like', 'dislike')",
            name="reaction_type_check"
        ),
    )
    
    @classmethod
    async def get_user_reaction(cls, session: AsyncSession, review_id: int, user_id: int) -> Optional["ReviewReactionModel"]:
        """Получение реакции пользователя на отзыв"""
        try:
            query = select(cls).where(
                cls.review_id == review_id,
                cls.user_id == user_id
            )
            result = await session.execute(query)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Ошибка при получении реакции пользователя {user_id} на отзыв {review_id}: {str(e)}")
            return None 