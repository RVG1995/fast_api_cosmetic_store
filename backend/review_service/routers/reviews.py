from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_session
from auth import get_current_user, require_user, User
from models import ReviewTypeEnum, ReviewModel, ReviewReactionModel
from schema import (
    ProductReviewCreate, StoreReviewCreate, ReactionCreate, 
    ReviewRead, ReviewStats, PaginatedResponse, UserReviewPermissions
)
from services import (
    create_product_review, create_store_review,
    get_product_reviews, get_store_reviews,
    add_review_reaction, get_product_review_stats, get_store_review_stats,
    get_review_by_id, invalidate_review_cache
)
import logging

# Настройка логирования
logger = logging.getLogger("review_service.routers.reviews")

# Создание роутера
router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
    responses={404: {"description": "Not found"}}
)

@router.post("/products", response_model=Optional[ReviewRead], status_code=status.HTTP_201_CREATED)
async def add_product_review(
    review_data: ProductReviewCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user)
):
    """
    Создание отзыва на товар.
    Только авторизованный пользователь с доставленным заказом, содержащим этот товар, может оставить отзыв.
    """
    review = await create_product_review(session, current_user, review_data)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать отзыв. Возможно, вы уже оставляли отзыв на этот товар или не имеете права оставлять отзыв."
        )
    
    # Создаем объект ответа вручную вместо использования from_orm_with_stats
    response_data = {
        "id": review.id,
        "user_id": review.user_id,
        "rating": review.rating,
        "content": review.content,
        "review_type": review.review_type,
        "product_id": review.product_id,
        "product_name": review.product_name,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "is_hidden": review.is_hidden,
        "is_anonymous": review.is_anonymous,
        "user_first_name": review.user_first_name,
        "user_last_name": review.user_last_name,
        "admin_comments": [],
        "reaction_stats": {"likes": 0, "dislikes": 0}
    }
    
    return ReviewRead.model_validate(response_data)

@router.post("/store", response_model=Optional[ReviewRead], status_code=status.HTTP_201_CREATED)
async def add_store_review(
    review_data: StoreReviewCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user)
):
    """
    Создание отзыва на магазин.
    Только авторизованный пользователь с хотя бы одним доставленным заказом может оставить отзыв.
    """
    review = await create_store_review(session, current_user, review_data)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать отзыв. Возможно, вы уже оставляли отзыв на магазин или не имеете права оставлять отзыв."
        )
    
    # Создаем объект ответа вручную вместо использования from_orm_with_stats
    response_data = {
        "id": review.id,
        "user_id": review.user_id,
        "rating": review.rating,
        "content": review.content,
        "review_type": review.review_type,
        "product_id": review.product_id,
        "product_name": review.product_name if hasattr(review, "product_name") else None,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "is_hidden": review.is_hidden,
        "is_anonymous": review.is_anonymous,
        "user_first_name": review.user_first_name,
        "user_last_name": review.user_last_name,
        "admin_comments": [],
        "reaction_stats": {"likes": 0, "dislikes": 0}
    }
    
    return ReviewRead.model_validate(response_data)

@router.get("/{review_id}", response_model=ReviewRead)
async def get_review(
    review_id: int = Path(..., description="ID отзыва"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получение отзыва по ID.
    Доступно для всех пользователей. Скрытые отзывы видны только администраторам.
    """
    # Определяем, может ли пользователь видеть скрытые отзывы
    include_hidden = current_user and (current_user.is_admin or current_user.is_super_admin)
    
    review = await get_review_by_id(session, review_id, include_hidden)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    return ReviewRead.from_orm_with_stats(review)

@router.get("/products/{product_id}", response_model=PaginatedResponse)
async def get_reviews_for_product(
    product_id: int = Path(..., description="ID товара"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=50, description="Количество записей на странице"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получение отзывов для товара.
    Доступно для всех пользователей. Скрытые отзывы видны только администраторам.
    """
    # Определяем, может ли пользователь видеть скрытые отзывы
    include_hidden = current_user and (current_user.is_admin or current_user.is_super_admin)
    
    reviews = await get_product_reviews(session, product_id, page, limit, include_hidden)
    return reviews

@router.get("/store/all", response_model=PaginatedResponse)
async def get_store_all_reviews(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=50, description="Количество записей на странице"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получение отзывов для магазина.
    Доступно для всех пользователей. Скрытые отзывы видны только администраторам.
    """
    # Определяем, может ли пользователь видеть скрытые отзывы
    include_hidden = current_user and (current_user.is_admin or current_user.is_super_admin)
    
    reviews = await get_store_reviews(session, page, limit, include_hidden)
    return reviews

@router.post("/reactions", status_code=status.HTTP_200_OK)
async def add_reaction(
    reaction_data: ReactionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user)
):
    """
    Добавление реакции (лайк/дизлайк) на отзыв.
    Доступно только для авторизованных пользователей.
    """
    reaction_result = await add_review_reaction(session, current_user, reaction_data)
    
    # Получаем обновленный отзыв для возврата клиенту
    review = await get_review_by_id(session, reaction_data.review_id)
    if not review:
        return {"status": "error", "message": "Отзыв не найден"}
    
    # Добавляем информацию о реакции пользователя
    user_reaction = await ReviewReactionModel.get_user_reaction(
        session, review.id, current_user.id
    )
    
    # Создаем объект ответа вручную со всеми необходимыми данными
    response_data = {
        "id": review.id,
        "user_id": review.user_id,
        "rating": review.rating,
        "content": review.content,
        "review_type": review.review_type,
        "product_id": review.product_id,
        "product_name": review.product_name,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "is_hidden": review.is_hidden,
        "is_anonymous": review.is_anonymous,
        "user_first_name": review.user_first_name,
        "user_last_name": review.user_last_name,
        "admin_comments": [
            {
                "id": comment.id,
                "review_id": comment.review_id,
                "admin_user_id": comment.admin_user_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "admin_name": comment.admin_name
            } for comment in review.admin_comments
        ],
        "reaction_stats": review.get_reaction_stats(),
        "user_reaction": user_reaction.reaction_type if user_reaction else None
    }
    
    return ReviewRead.model_validate(response_data)

@router.get("/reactions/{review_id}", status_code=status.HTTP_200_OK)
async def get_user_reaction(
    review_id: int = Path(..., description="ID отзыва"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получение реакции пользователя на отзыв.
    Доступно для авторизованных пользователей.
    """
    if not current_user:
        return {"has_reaction": False, "reaction_type": None}
    
    try:
        # Получаем реакцию пользователя
        reaction = await ReviewReactionModel.get_user_reaction(
            session, review_id, current_user.id
        )
        
        if reaction:
            return {
                "has_reaction": True,
                "reaction_type": reaction.reaction_type
            }
        else:
            return {"has_reaction": False, "reaction_type": None}
    except Exception as e:
        logger.error(f"Ошибка при получении реакции пользователя на отзыв {review_id}: {str(e)}")
        return {"has_reaction": False, "reaction_type": None}

@router.delete("/reactions/{review_id}", status_code=status.HTTP_200_OK)
async def delete_reaction(
    review_id: int = Path(..., description="ID отзыва"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user)
):
    """
    Удаление реакции (лайк/дизлайк) на отзыв.
    Доступно только для авторизованных пользователей.
    """
    # Получаем текущую реакцию пользователя
    user_reaction = await ReviewReactionModel.get_user_reaction(
        session, review_id, current_user.id
    )
    
    if user_reaction:
        # Удаляем реакцию
        await session.delete(user_reaction)
        await session.commit()
        
        # Инвалидируем кэш в отдельном блоке try после успешного коммита
        try:
            await invalidate_review_cache(review_id)
        except Exception as cache_error:
            logger.error(f"Ошибка при инвалидации кэша после удаления реакции на отзыв {review_id}: {str(cache_error)}")
    
    # Получаем обновленный отзыв для возврата клиенту
    review = await get_review_by_id(session, review_id)
    if not review:
        return {"status": "error", "message": "Отзыв не найден"}
    
    # Создаем объект ответа вручную со всеми необходимыми данными
    response_data = {
        "id": review.id,
        "user_id": review.user_id,
        "rating": review.rating,
        "content": review.content,
        "review_type": review.review_type,
        "product_id": review.product_id,
        "product_name": review.product_name,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "is_hidden": review.is_hidden,
        "is_anonymous": review.is_anonymous,
        "user_first_name": review.user_first_name,
        "user_last_name": review.user_last_name,
        "admin_comments": [
            {
                "id": comment.id,
                "review_id": comment.review_id,
                "admin_user_id": comment.admin_user_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "admin_name": comment.admin_name
            } for comment in review.admin_comments
        ],
        "reaction_stats": review.get_reaction_stats(),
        "user_reaction": None  # Реакция удалена
    }
    
    return ReviewRead.model_validate(response_data)

@router.get("/products/{product_id}/stats", response_model=ReviewStats)
async def get_product_stats(
    product_id: int = Path(..., description="ID товара"),
    session: AsyncSession = Depends(get_session)
):
    """
    Получение статистики отзывов о товаре.
    Доступно для всех пользователей.
    """
    stats = await get_product_review_stats(session, product_id)
    # Преобразуем строковые ключи в целочисленные, если нужно
    if isinstance(stats, dict) and "rating_counts" in stats:
        if any(isinstance(k, str) for k in stats["rating_counts"].keys()):
            stats["rating_counts"] = {int(k): v for k, v in stats["rating_counts"].items()}
    return stats

@router.get("/permissions/check", response_model=UserReviewPermissions)
async def check_review_permissions(
    product_id: Optional[int] = Query(None, description="ID товара для проверки возможности оставить отзыв"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user)
):
    """
    Проверка прав пользователя на оставление отзывов.
    Доступно только для авторизованных пользователей.
    """
    result = UserReviewPermissions()
    
    # Проверяем возможность оставить отзыв на магазин
    can_review_store = await ReviewModel.check_user_can_review_store(session, current_user.id)
    result.can_review_store = can_review_store
    
    # Проверяем, оставлял ли пользователь отзыв на магазин
    existing_store_review_query = await session.execute(
        text(f"SELECT id FROM reviews WHERE user_id = {current_user.id} AND review_type = '{ReviewTypeEnum.STORE.value}'")
    )
    existing_store_review = existing_store_review_query.scalar_one_or_none()
    result.has_reviewed_store = existing_store_review is not None
    
    # Если указан product_id, проверяем возможность оставить отзыв на товар
    if product_id:
        can_review_product = await ReviewModel.check_user_can_review_product(session, current_user.id, product_id)
        result.can_review_product = can_review_product
        
        # Проверяем, оставлял ли пользователь отзыв на этот товар
        existing_product_review_query = await session.execute(
            text(f"SELECT id FROM reviews WHERE user_id = {current_user.id} AND product_id = {product_id} AND review_type = '{ReviewTypeEnum.PRODUCT.value}'")
        )
        existing_product_review = existing_product_review_query.scalar_one_or_none()
        result.has_reviewed_product = existing_product_review is not None
    
    return result

@router.get("/store/stats", response_model=ReviewStats)
async def get_store_stats(
    session: AsyncSession = Depends(get_session)
):
    """
    Получение статистики отзывов о магазине.
    Доступно для всех пользователей.
    """
    stats = await get_store_review_stats(session)
    # Преобразуем строковые ключи в целочисленные, если нужно
    if isinstance(stats, dict) and "rating_counts" in stats:
        if any(isinstance(k, str) for k in stats["rating_counts"].keys()):
            stats["rating_counts"] = {int(k): v for k, v in stats["rating_counts"].items()}
    return stats 