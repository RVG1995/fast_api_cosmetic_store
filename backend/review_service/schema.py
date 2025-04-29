"""Схемы Pydantic для сервиса отзывов."""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict


class ReviewType(str, Enum):
    """Типы отзывов в системе."""
    PRODUCT = "product"
    STORE = "store"


class ReactionType(str, Enum):
    """Типы реакций на отзывы."""
    LIKE = "like"
    DISLIKE = "dislike"


class ReviewBase(BaseModel):
    """Базовая модель отзыва с рейтингом и текстовым содержимым."""
    
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    content: Optional[str] = Field(None, max_length=2000, description="Текстовый отзыв")
    
    @field_validator('rating')
    def validate_rating(cls, value):
        """Проверяет, что рейтинг находится в диапазоне от 1 до 5."""
        if value < 1 or value > 5:
            raise ValueError("Рейтинг должен быть от 1 до 5")
        return value
        
    @field_validator('content')
    def validate_content(cls, value):
        """Проверяет, что текст отзыва не пустой и содержит минимум 3 символа."""
        # Если значение пустое или None, возвращаем пустую строку
        if value is None or value == "":
            return ""
        # Если есть текст, проверяем минимальную длину
        if len(value) < 3:
            raise ValueError("Если вы добавляете текст отзыва, он должен содержать минимум 3 символа")
        return value


class ProductReviewCreate(ReviewBase):
    """Модель для создания отзыва о товаре."""
    product_id: int = Field(..., description="ID товара")
    is_anonymous: bool = False


class StoreReviewCreate(ReviewBase):
    """Модель для создания отзыва о магазине."""
    is_anonymous: bool = False


class AdminCommentBase(BaseModel):
    """Базовая модель комментария администратора."""
    content: str = Field(..., min_length=3, max_length=2000, description="Текст комментария администратора")


class AdminCommentCreate(AdminCommentBase):
    """Модель для создания комментария администратора к отзыву."""
    review_id: int = Field(..., description="ID отзыва")


class ReactionCreate(BaseModel):
    """Модель для создания реакции на отзыв."""
    review_id: int = Field(..., description="ID отзыва")
    reaction_type: ReactionType = Field(..., description="Тип реакции (лайк/дизлайк)")


class ReactionRead(ReactionCreate):
    """Модель для чтения реакции на отзыв."""
    id: int
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AdminCommentRead(AdminCommentBase):
    """Модель для чтения комментария администратора к отзыву."""
    id: int
    review_id: int
    admin_user_id: int
    admin_name: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ReviewRead(BaseModel):
    """Модель для чтения отзыва с дополнительной информацией."""
    id: int
    user_id: int
    rating: int
    content: Optional[str] = None
    review_type: str
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_hidden: bool
    is_anonymous: bool = False
    user_first_name: str
    user_last_name: str
    admin_comments: List[AdminCommentRead] = []
    reaction_stats: Dict[str, int] = {"likes": 0, "dislikes": 0}
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_orm_with_stats(cls, obj):
        """Преобразует ORM объект в модель ReviewRead с подсчетом статистики реакций."""
        data = {}
        for field in obj.__dict__:
            if not field.startswith('_'):
                data[field] = getattr(obj, field)
        
        # Устанавливаем пустую статистику по реакциям по умолчанию
        # вместо вызова потенциально опасного метода
        data['reaction_stats'] = {"likes": 0, "dislikes": 0}
        
        # Если у объекта уже загружены реакции, считаем их
        if hasattr(obj, 'reactions') and isinstance(obj.reactions, list):
            likes = 0
            dislikes = 0
            for reaction in obj.reactions:
                if reaction.reaction_type == 'like':
                    likes += 1
                elif reaction.reaction_type == 'dislike':
                    dislikes += 1
            data['reaction_stats'] = {"likes": likes, "dislikes": dislikes}
        
        # Комментарии администратора
        data['admin_comments'] = []
        if hasattr(obj, 'admin_comments') and isinstance(obj.admin_comments, list):
            data['admin_comments'] = [
                {
                    "id": comment.id,
                    "review_id": comment.review_id,
                    "admin_user_id": comment.admin_user_id,
                    "admin_name": comment.admin_name,
                    "content": comment.content,
                    "created_at": comment.created_at,
                    "updated_at": comment.updated_at
                }
                for comment in obj.admin_comments
            ]
        
        # Логируем данные для отладки
        logger = logging.getLogger("review_service.schema")
        logger.info("Преобразование объекта %s в модель ReviewRead: %s", obj.id, data)
        
        return cls.model_validate(data)


class AdminReviewUpdate(BaseModel):
    """Модель для обновления отзыва администратором."""
    is_hidden: Optional[bool] = None


class PaginatedResponse(BaseModel):
    """Модель для пагинированного ответа."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class ReviewStats(BaseModel):
    """Модель для статистики отзывов."""
    average_rating: float
    total_reviews: int
    rating_counts: Dict[int, int]  # Ключ - рейтинг (1-5), значение - количество отзывов с таким рейтингом


class BatchProductReviewStatsRequest(BaseModel):
    """Модель для запроса статистики отзывов по нескольким товарам."""
    product_ids: List[int] = Field(..., description="Список ID товаров для получения статистики")


class BatchProductReviewStatsResponse(BaseModel):
    """Модель для ответа со статистикой отзывов по нескольким товарам."""
    results: Dict[str, ReviewStats] = Field(..., description="Статистика отзывов по товарам, ключ - ID товара")


class UserReviewPermissions(BaseModel):
    """Модель для прав пользователя на работу с отзывами."""
    can_review_product: bool = False
    can_review_store: bool = False
    has_reviewed_product: bool = False
    has_reviewed_store: bool = False 
