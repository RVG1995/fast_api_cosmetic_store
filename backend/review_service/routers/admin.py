from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from auth import require_admin, User
from models import ReviewTypeEnum
from schema import (
    AdminCommentCreate, AdminCommentRead, 
    ReviewRead, AdminReviewUpdate, PaginatedResponse
)
from services import (
    create_admin_comment, get_review_by_id,
    get_product_reviews, get_store_reviews,
    toggle_review_visibility
)
from config import logger, DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

# Создание роутера
router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin_reviews"],
    responses={404: {"description": "Not found"}}
)

@router.post("/comments", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def add_admin_comment(
    comment_data: AdminCommentCreate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Добавление комментария администратора к отзыву.
    Доступно только для администраторов.
    """
    comment = await create_admin_comment(session, admin, comment_data)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать комментарий. Отзыв не найден."
        )
        
    # Получаем обновленный отзыв для возврата полных данных
    review = await get_review_by_id(session, comment_data.review_id, include_hidden=True)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден после добавления комментария."
        )
        
    # Создаем объект ответа вручную
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
        "reaction_stats": review.get_reaction_stats()
    }
    
    return ReviewRead.model_validate(response_data)

@router.patch("/{review_id}", response_model=ReviewRead,dependencies=[Depends(require_admin)])
async def update_review(
    review_id: int = Path(..., description="ID отзыва"),
    review_data: AdminReviewUpdate = Body(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Обновление информации об отзыве (скрытие/отображение).
    Доступно только для администраторов.
    """
    if review_data.is_hidden is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать значение параметра is_hidden"
        )
    
    review_dict = await toggle_review_visibility(session, review_id, review_data.is_hidden)
    if not review_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    
    # Возвращаем объект ReviewRead, созданный из полученного словаря
    return ReviewRead.model_validate(review_dict)

@router.get("/products/{product_id}", response_model=PaginatedResponse,dependencies=[Depends(require_admin)])
async def get_product_reviews_admin(
    product_id: int = Path(..., description="ID товара"),
    page: int = Query(DEFAULT_PAGE, ge=1, description="Номер страницы"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Количество записей на странице"),
    include_hidden: bool = Query(True, description="Включать скрытые отзывы"),
    session: AsyncSession = Depends(get_session),
):
    """
    Получение отзывов для товара, включая скрытые.
    Доступно только для администраторов.
    """
    reviews = await get_product_reviews(session, product_id, page, limit, include_hidden)
    return reviews

@router.get("/store", response_model=PaginatedResponse,dependencies=[Depends(require_admin)])
async def get_store_reviews_admin(
    page: int = Query(DEFAULT_PAGE, ge=1, description="Номер страницы"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Количество записей на странице"),
    include_hidden: bool = Query(True, description="Включать скрытые отзывы"),
    session: AsyncSession = Depends(get_session),
):
    """
    Получение отзывов для магазина, включая скрытые.
    Доступно только для администраторов.
    """
    reviews = await get_store_reviews(session, page, limit, include_hidden)
    return reviews

@router.get("/{review_id}", response_model=ReviewRead,dependencies=[Depends(require_admin)])
async def get_review_admin(
    review_id: int = Path(..., description="ID отзыва"),
    session: AsyncSession = Depends(get_session),
):
    """
    Получение отзыва по ID, включая скрытые.
    Доступно только для администраторов.
    """
    review = await get_review_by_id(session, review_id, include_hidden=True)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
        
    # Создаем объект ответа вручную
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
        "reaction_stats": review.get_reaction_stats()
    }
    
    return ReviewRead.model_validate(response_data) 