from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from database import get_session
from auth import get_current_user, require_user, User
from models import ReviewTypeEnum, ReviewModel, ReviewReactionModel, AdminCommentModel
from schema import (
    ProductReviewCreate, StoreReviewCreate, ReactionCreate, 
    ReviewRead, ReviewStats, PaginatedResponse, UserReviewPermissions,
    BatchProductReviewStatsRequest, BatchProductReviewStatsResponse
)
from services import (
    create_product_review, create_store_review,
    get_product_reviews, get_store_reviews, get_product_review_stats, get_store_review_stats,
    get_review_by_id, get_batch_product_review_stats
)
from cache import (
    cache_get, cache_set, CACHE_KEYS, CACHE_TTL, 
    invalidate_review_cache, cache_delete, cache_delete_pattern
)
from config import logger, DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

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
    page: int = Query(DEFAULT_PAGE, ge=1, description="Номер страницы"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Количество записей на странице"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получение отзывов для товара.
    Доступно для всех пользователей. Скрытые отзывы видны только администраторам.
    """
    # Определяем, может ли пользователь видеть скрытые отзывы
    include_hidden = current_user and (current_user.is_admin or current_user.is_super_admin)
    
    logger.debug(f"Запрос отзывов для товара {product_id}, страница {page}, лимит {limit}, include_hidden={include_hidden}")
    reviews = await get_product_reviews(session, product_id, page, limit, include_hidden)
    return reviews

@router.get("/store/all", response_model=PaginatedResponse)
async def get_store_all_reviews(
    page: int = Query(DEFAULT_PAGE, ge=1, description="Номер страницы"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Количество записей на странице"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Получение отзывов для магазина.
    Доступно для всех пользователей. Скрытые отзывы видны только администраторам.
    """
    # Определяем, может ли пользователь видеть скрытые отзывы
    include_hidden = current_user and (current_user.is_admin or current_user.is_super_admin)
    
    logger.debug(f"Запрос отзывов для магазина, страница {page}, лимит {limit}, include_hidden={include_hidden}")
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
    try:
        # Проверим существование отзыва
        review_id = reaction_data.review_id
        review_query = await session.execute(
            select(ReviewModel).where(ReviewModel.id == review_id)
        )
        review = review_query.scalars().first()
        
        if not review:
            return {"status": "error", "message": "Отзыв не найден"}
            
        # Кэшируем данные об отзыве, чтобы можно было правильно инвалидировать кэш
        product_id = review.product_id
        review_type = review.review_type
        
        # Загружаем все существующие реакции для отзыва до внесения изменений
        reactions_query = await session.execute(
            select(ReviewReactionModel).where(ReviewReactionModel.review_id == review_id)
        )
        existing_reactions = reactions_query.scalars().all()
        
        # Находим реакцию текущего пользователя
        user_reaction = None
        for reaction in existing_reactions:
            if reaction.user_id == current_user.id:
                user_reaction = reaction
                break
        
        # Обрабатываем реакцию
        if user_reaction:
            # Если реакция уже существует и такая же - удаляем
            if user_reaction.reaction_type == reaction_data.reaction_type:
                await session.delete(user_reaction)
                await session.commit()
                user_reaction = None
                logger.info(f"Удалена реакция пользователя {current_user.id} на отзыв {review_id}")
            else:
                # Если тип отличается - обновляем
                user_reaction.reaction_type = reaction_data.reaction_type.value
                await session.commit()
                logger.info(f"Обновлена реакция пользователя {current_user.id} на отзыв {review_id}: {reaction_data.reaction_type.value}")
        else:
            # Создаем новую реакцию
            new_reaction = ReviewReactionModel(
                review_id=review_id,
                user_id=current_user.id,
                reaction_type=reaction_data.reaction_type.value
            )
            session.add(new_reaction)
            await session.commit()
            user_reaction = new_reaction
            logger.info(f"Создана реакция пользователя {current_user.id} на отзыв {review_id}: {reaction_data.reaction_type.value}")
        
        # Инвалидируем только кэш конкретного отзыва вместо всех связанных кэшей
        try:
            # Инвалидируем кэш отзыва
            review_cache_key = f"{CACHE_KEYS['review']}{review_id}"
            logger.debug(f"Инвалидация кэша отзыва {review_id}: {review_cache_key}")
            await cache_delete(review_cache_key)
            
            # В зависимости от типа отзыва, инвалидируем соответствующие кэши страниц
            if review_type == 'product' and product_id:
                # Для отзывов о товарах инвалидируем только страницы с отзывами этого товара
                logger.debug(f"Инвалидация кэша списков отзывов для товара {product_id}")
                await invalidate_review_cache(review_id)
            elif review_type == 'store':
                # Для отзывов о магазине инвалидируем соответствующие кэши
                logger.debug(f"Инвалидация кэша отзывов о магазине")
                await invalidate_review_cache(review_id)
                
        except Exception as cache_error:
            logger.error(f"Ошибка при инвалидации кэша для отзыва {review_id}: {str(cache_error)}")
        
        # Загружаем свежие реакции для отзыва для обновления статистики
        fresh_reactions_query = await session.execute(
            select(ReviewReactionModel).where(ReviewReactionModel.review_id == review_id)
        )
        fresh_reactions = fresh_reactions_query.scalars().all()
        
        # Считаем статистику
        likes = sum(1 for r in fresh_reactions if r.reaction_type == 'like')
        dislikes = sum(1 for r in fresh_reactions if r.reaction_type == 'dislike')
        reaction_stats = {"likes": likes, "dislikes": dislikes}
        
        # Формируем детали отзыва для ответа
        admin_comments_query = await session.execute(
            select(AdminCommentModel).where(AdminCommentModel.review_id == review_id)
        )
        admin_comments = admin_comments_query.scalars().all()
        
        # Создаем объект ответа
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
                } for comment in admin_comments
            ],
            "reaction_stats": reaction_stats,
            "user_reaction": user_reaction.reaction_type if user_reaction else None
        }
        
        logger.info(f"Обработана реакция для отзыва {review.id}, пользователь {current_user.id}, " +
                  f"тип реакции: {user_reaction.reaction_type if user_reaction else 'None'}, " +
                  f"стат: likes={reaction_stats['likes']}, dislikes={reaction_stats['dislikes']}")
        
        return ReviewRead.model_validate(response_data)
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при обработке реакции: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке реакции: {str(e)}"
        )

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
    # Получаем отзыв для определения типа и связанных данных
    review = await ReviewModel.get_by_id(session, review_id)
    if not review:
        return {"status": "error", "message": "Отзыв не найден"}
    
    # Сохраняем данные отзыва для инвалидации кэша
    product_id = review.product_id
    review_type = review.review_type
    
    # Получаем текущую реакцию пользователя
    user_reaction = await ReviewReactionModel.get_user_reaction(
        session, review_id, current_user.id
    )
    
    if user_reaction:
        # Удаляем реакцию
        await session.delete(user_reaction)
        await session.commit()
        
        # Инвалидируем только кэш конкретного отзыва
        try:
            # Инвалидируем кэш отзыва
            review_cache_key = f"{CACHE_KEYS['review']}{review_id}"
            logger.debug(f"Инвалидация кэша отзыва {review_id}: {review_cache_key}")
            await cache_delete(review_cache_key)
            
            # В зависимости от типа отзыва, инвалидируем соответствующие кэши страниц
            if review_type == 'product' and product_id:
                # Для отзывов о товарах инвалидируем страницы с отзывами этого товара
                product_reviews_key = f"{CACHE_KEYS['product_reviews']}{product_id}:*"
                logger.debug(f"Инвалидация кэша списков отзывов для товара {product_id}: {product_reviews_key}")
                await cache_delete_pattern(product_reviews_key)
            elif review_type == 'store':
                # Для отзывов о магазине инвалидируем соответствующие кэши
                store_reviews_key = f"{CACHE_KEYS['store_reviews']}*"
                logger.debug(f"Инвалидация кэша отзывов о магазине: {store_reviews_key}")
                await cache_delete_pattern(store_reviews_key)
        except Exception as cache_error:
            logger.error(f"Ошибка при инвалидации кэша после удаления реакции на отзыв {review_id}: {str(cache_error)}")
    
    # Получаем обновленный отзыв для возврата клиенту с актуальными данными о реакциях
    updated_review = await get_review_by_id(session, review_id)
    if not updated_review:
        return {"status": "error", "message": "Отзыв не найден после удаления реакции"}
    
    # Создаем объект ответа вручную со всеми необходимыми данными
    response_data = {
        "id": updated_review.id,
        "user_id": updated_review.user_id,
        "rating": updated_review.rating,
        "content": updated_review.content,
        "review_type": updated_review.review_type,
        "product_id": updated_review.product_id,
        "product_name": updated_review.product_name,
        "created_at": updated_review.created_at,
        "updated_at": updated_review.updated_at,
        "is_hidden": updated_review.is_hidden,
        "is_anonymous": updated_review.is_anonymous,
        "user_first_name": updated_review.user_first_name,
        "user_last_name": updated_review.user_last_name,
        "admin_comments": [
            {
                "id": comment.id,
                "review_id": comment.review_id,
                "admin_user_id": comment.admin_user_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
                "admin_name": comment.admin_name
            } for comment in updated_review.admin_comments
        ],
        "reaction_stats": updated_review.get_reaction_stats(),
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
    logger.debug(f"Запрос статистики отзывов для товара {product_id}")
    stats = await get_product_review_stats(session, product_id)
    # Преобразуем строковые ключи в целочисленные, если нужно
    if isinstance(stats, dict) and "rating_counts" in stats:
        if any(isinstance(k, str) for k in stats["rating_counts"].keys()):
            stats["rating_counts"] = {int(k): v for k, v in stats["rating_counts"].items()}
    return stats

@router.post("/products/batch-stats", response_model=BatchProductReviewStatsResponse)
async def get_batch_product_stats(
    request: BatchProductReviewStatsRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Пакетное получение статистики отзывов для нескольких товаров.
    Принимает список ID товаров и возвращает статистику для каждого товара одним запросом.
    Доступно для всех пользователей.
    """
    if not request.product_ids:
        return {"results": {}}
    
    # Ограничиваем количество запрашиваемых товаров
    if len(request.product_ids) > 100:
        request.product_ids = request.product_ids[:100]
    
    logger.debug(f"Запрос пакетной статистики отзывов для {len(request.product_ids)} товаров")
    # Получаем статистику для всех товаров
    stats = await get_batch_product_review_stats(session, request.product_ids)
    
    # Преобразуем строковые ключи рейтингов в целочисленные, если нужно
    for product_id, product_stats in stats.items():
        if "rating_counts" in product_stats:
            if any(isinstance(k, str) for k in product_stats["rating_counts"].keys()):
                product_stats["rating_counts"] = {int(k): v for k, v in product_stats["rating_counts"].items()}
    
    return {"results": stats}

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
    
    # Формируем ключ кэша для проверки отзыва на магазин
    store_check_cache_key = f"{CACHE_KEYS['user_permissions']}store_check:{current_user.id}"
    cached_store_data = await cache_get(store_check_cache_key)
    
    if cached_store_data is not None:
        logger.debug(f"Данные о проверке прав на отзыв о магазине получены из кэша: user_id={current_user.id}")
        result.can_review_store = cached_store_data.get("can_review_store", False)
        result.has_reviewed_store = cached_store_data.get("has_reviewed_store", False)
    else:
        # Проверяем возможность оставить отзыв на магазин
        can_review_store = await ReviewModel.check_user_can_review_store(session, current_user.id)
        result.can_review_store = can_review_store
        
        # Проверяем, оставлял ли пользователь отзыв на магазин
        existing_store_review_query = await session.execute(
            text(f"SELECT id FROM reviews WHERE user_id = {current_user.id} AND review_type = '{ReviewTypeEnum.STORE.value}'")
        )
        existing_store_review = existing_store_review_query.scalar_one_or_none()
        result.has_reviewed_store = existing_store_review is not None
        
        # Кэшируем результат
        store_cache_data = {
            "can_review_store": result.can_review_store,
            "has_reviewed_store": result.has_reviewed_store
        }
        await cache_set(store_check_cache_key, store_cache_data, CACHE_TTL["permissions"])
        logger.debug(f"Результаты проверки прав на отзыв о магазине сохранены в кэш: user_id={current_user.id}")
    
    # Если указан product_id, проверяем возможность оставить отзыв на товар
    if product_id:
        # Формируем ключ кэша для проверки отзыва на товар
        product_check_cache_key = f"{CACHE_KEYS['user_permissions']}product_check:{current_user.id}:{product_id}"
        cached_product_data = await cache_get(product_check_cache_key)
        
        if cached_product_data is not None:
            logger.debug(f"Данные о проверке прав на отзыв о товаре получены из кэша: user_id={current_user.id}, product_id={product_id}")
            result.can_review_product = cached_product_data.get("can_review_product", False)
            result.has_reviewed_product = cached_product_data.get("has_reviewed_product", False)
        else:
            can_review_product = await ReviewModel.check_user_can_review_product(session, current_user.id, product_id)
            result.can_review_product = can_review_product
            
            # Проверяем, оставлял ли пользователь отзыв на этот товар
            existing_product_review_query = await session.execute(
                text(f"SELECT id FROM reviews WHERE user_id = {current_user.id} AND product_id = {product_id} AND review_type = '{ReviewTypeEnum.PRODUCT.value}'")
            )
            existing_product_review = existing_product_review_query.scalar_one_or_none()
            result.has_reviewed_product = existing_product_review is not None
            
            # Кэшируем результат
            product_cache_data = {
                "can_review_product": result.can_review_product,
                "has_reviewed_product": result.has_reviewed_product
            }
            await cache_set(product_check_cache_key, product_cache_data, CACHE_TTL["permissions"])
            logger.debug(f"Результаты проверки прав на отзыв о товаре сохранены в кэш: user_id={current_user.id}, product_id={product_id}")
    
    return result

@router.get("/store/stats", response_model=ReviewStats)
async def get_store_stats(
    session: AsyncSession = Depends(get_session)
):
    """
    Получение статистики отзывов о магазине.
    Доступно для всех пользователей.
    """
    logger.debug("Запрос статистики отзывов для магазина")
    stats = await get_store_review_stats(session)
    # Преобразуем строковые ключи в целочисленные, если нужно
    if isinstance(stats, dict) and "rating_counts" in stats:
        if any(isinstance(k, str) for k in stats["rating_counts"].keys()):
            stats["rating_counts"] = {int(k): v for k, v in stats["rating_counts"].items()}
    return stats

@router.post("/reactions/delete", status_code=status.HTTP_200_OK)
async def delete_reaction_post_method(
    review_data: Dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_user)
):
    """
    Удаление реакции (лайк/дизлайк) на отзыв по POST запросу.
    Альтернативный метод для клиентов, которые не могут отправить DELETE запрос.
    Доступно только для авторизованных пользователей.
    """
    review_id = review_data.get("review_id")
    
    if not review_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать review_id"
        )
    
    # Получаем текущую реакцию пользователя
    user_reaction = await ReviewReactionModel.get_user_reaction(
        session, review_id, current_user.id
    )
    
    # Сохраняем тип реакции для логирования
    old_reaction_type = user_reaction.reaction_type if user_reaction else None
    
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
    
    # Загружаем все реакции для отзыва для точного подсчета
    reactions_query = select(ReviewReactionModel).where(ReviewReactionModel.review_id == review.id)
    reactions_result = await session.execute(reactions_query)
    reactions = reactions_result.scalars().all()
    
    # Вручную устанавливаем реакции для отзыва
    setattr(review, 'reactions', reactions)
    
    # Перепроверяем, что реакция точно удалена
    user_reaction_after = await ReviewReactionModel.get_user_reaction(
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
        "user_reaction": user_reaction_after.reaction_type if user_reaction_after else None
    }
    
    logger.info(f"Удалена реакция для отзыва {review.id}, пользователь {current_user.id}, " +
               f"старый тип реакции: {old_reaction_type}, новая реакция: {response_data['user_reaction']}, " +
               f"стат: likes={response_data['reaction_stats']['likes']}, dislikes={response_data['reaction_stats']['dislikes']}")
    
    return ReviewRead.model_validate(response_data) 