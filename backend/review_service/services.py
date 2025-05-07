import os
import httpx
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from models import ReviewModel, AdminCommentModel, ReviewReactionModel, ReviewTypeEnum
from schema import ProductReviewCreate, StoreReviewCreate, AdminCommentCreate, ReactionCreate, ReviewRead, ReviewStats
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, bindparam
from auth import User
from math import ceil
from cache import (
    cache_get, cache_set, invalidate_review_cache,
    invalidate_product_reviews_cache, invalidate_store_reviews_cache,
    invalidate_user_reviews_cache, CACHE_KEYS, CACHE_TTL
)
from sqlalchemy.sql import select, func
from config import settings, logger

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_service.services")

# URL других сервисов
ORDER_SERVICE_URL = settings.ORDER_SERVICE_URL
PRODUCT_SERVICE_URL = settings.PRODUCT_SERVICE_URL


class ProductApi:
    """Класс для взаимодействия с API сервиса продуктов"""
    
    @staticmethod
    async def get_product_details(product_id: int, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Получение информации о товаре по ID"""
        try:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
            url = f"{PRODUCT_SERVICE_URL}/products/{product_id}"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Успешно получена информация о товаре: {product_id}")
                    return data
                else:
                    logger.warning(f"Ошибка при получении информации о товаре {product_id}. Код: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при обращении к сервису продуктов: {str(e)}")
            return None


class OrderApi:
    """Класс для взаимодействия с API сервиса заказов"""
    
    @staticmethod
    async def check_user_can_review_product(user_id: int, product_id: int, token: Optional[str] = None) -> bool:
        """
        Проверка, может ли пользователь оставить отзыв на товар
        (заказал товар и статус заказа 'delivered')
        """
        try:
            # Проверяем кэш
            cache_key = f"{CACHE_KEYS['permissions']}product:{user_id}:{product_id}"
            cached_result = await cache_get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Результат проверки возможности оставить отзыв получен из кэша: user_id={user_id}, product_id={product_id}, result={cached_result}")
                return cached_result
                
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
            url = f"{ORDER_SERVICE_URL}/orders/check-can-review"
            data = {
                "user_id": user_id,
                "product_id": product_id
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    can_review = result.get("can_review", False)
                    logger.info(f"Проверка возможности оставить отзыв: user_id={user_id}, product_id={product_id}, result={can_review}")
                    
                    # Кэшируем результат
                    await cache_set(cache_key, can_review, CACHE_TTL["permissions"])
                    
                    return can_review
                else:
                    logger.warning(f"Ошибка при проверке возможности оставить отзыв. Код: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при обращении к сервису заказов: {str(e)}")
            return False
    
    @staticmethod
    async def check_user_can_review_store(user_id: int, token: Optional[str] = None) -> bool:
        """
        Проверка, может ли пользователь оставить отзыв на магазин
        (имеет хотя бы один заказ со статусом 'delivered')
        """
        try:
            # Проверяем кэш
            cache_key = f"{CACHE_KEYS['permissions']}store:{user_id}"
            cached_result = await cache_get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Результат проверки возможности оставить отзыв на магазин получен из кэша: user_id={user_id}, result={cached_result}")
                return cached_result
                
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
            url = f"{ORDER_SERVICE_URL}/orders/check-can-review-store"
            data = {
                "user_id": user_id
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    can_review = result.get("can_review", False)
                    logger.info(f"Проверка возможности оставить отзыв на магазин: user_id={user_id}, result={can_review}")
                    
                    # Кэшируем результат
                    await cache_set(cache_key, can_review, CACHE_TTL["permissions"])
                    
                    return can_review
                else:
                    logger.warning(f"Ошибка при проверке возможности оставить отзыв на магазин. Код: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при обращении к сервису заказов: {str(e)}")
            return False


# Создаем экземпляры для использования в других модулях
product_api = ProductApi()
order_api = OrderApi()


async def create_product_review(
    session: AsyncSession,
    user: User,
    review_data: ProductReviewCreate
) -> Optional[ReviewModel]:
    """
    Создание отзыва на товар
    
    Args:
        session: Сессия базы данных
        user: Пользователь
        review_data: Данные отзыва
        
    Returns:
        ReviewModel: Созданный отзыв или None в случае ошибки
    """
    try:
        # Логируем данные пользователя для отладки
        logger.info(f"Данные пользователя для отзыва: id={user.id}, email={user.email}, имя={user.first_name}, фамилия={user.last_name}")
        
        # Проверяем, что пользователь может оставить отзыв на этот товар
        can_review = await ReviewModel.check_user_can_review_product(session, user.id, review_data.product_id)
        if not can_review:
            logger.warning(f"Пользователь {user.id} не может оставить отзыв на товар {review_data.product_id}")
            return None
        
        # Проверяем, не оставил ли пользователь уже отзыв на этот товар
        existing_review_query = await session.execute(
            text(f"SELECT id FROM reviews WHERE user_id = {user.id} AND product_id = {review_data.product_id} AND review_type = '{ReviewTypeEnum.PRODUCT.value}'")
        )
        existing_review = existing_review_query.scalar_one_or_none()
        if existing_review:
            logger.warning(f"Пользователь {user.id} уже оставил отзыв на товар {review_data.product_id}")
            return None
        
        # Получаем информацию о товаре
        product_info = await product_api.get_product_details(review_data.product_id)
        if not product_info:
            logger.error(f"Не удалось получить информацию о товаре {review_data.product_id}")
            return None
        
        # Обеспечиваем значения по умолчанию для данных пользователя 
        first_name = user.first_name or "Пользователь"
        last_name = user.last_name or ""
        email = user.email or f"user{user.id}@example.com"
        
        # Если отзыв анонимный, изменяем имя и фамилию
        if review_data.is_anonymous:
            first_name = "Пользователь скрыл свои данные"
            last_name = ""
        
        # Создаем отзыв
        review = ReviewModel(
            user_id=user.id,
            rating=review_data.rating,
            content=review_data.content,
            review_type=ReviewTypeEnum.PRODUCT.value,
            product_id=review_data.product_id,
            product_name=product_info.get("name", ""),
            user_first_name=first_name,
            user_last_name=last_name,
            user_email=email,
            is_anonymous=review_data.is_anonymous
        )
        session.add(review)
        await session.commit()
        await session.refresh(review)
        
        # Инвалидируем кэш
        await invalidate_product_reviews_cache(review_data.product_id)
        await invalidate_user_reviews_cache(user.id)
        
        logger.info(f"Создан отзыв на товар: user_id={user.id}, product_id={review_data.product_id}, rating={review_data.rating}")
        return review
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при создании отзыва на товар: {str(e)}")
        return None

async def create_store_review(
    session: AsyncSession,
    user: User,
    review_data: StoreReviewCreate
) -> Optional[ReviewModel]:
    """
    Создание отзыва на магазин
    
    Args:
        session: Сессия базы данных
        user: Пользователь
        review_data: Данные отзыва
        
    Returns:
        ReviewModel: Созданный отзыв или None в случае ошибки
    """
    try:
        # Логируем данные пользователя для отладки
        logger.info(f"Данные пользователя для отзыва на магазин: id={user.id}, email={user.email}, имя={user.first_name}, фамилия={user.last_name}")
        
        # Проверяем, что пользователь может оставить отзыв на магазин
        can_review = await ReviewModel.check_user_can_review_store(session, user.id)
        if not can_review:
            logger.warning(f"Пользователь {user.id} не может оставить отзыв на магазин")
            return None
        
        # Проверяем, не оставил ли пользователь уже отзыв на магазин
        existing_review_query = await session.execute(
            text(f"SELECT id FROM reviews WHERE user_id = {user.id} AND review_type = '{ReviewTypeEnum.STORE.value}'")
        )
        existing_review = existing_review_query.scalar_one_or_none()
        if existing_review:
            logger.warning(f"Пользователь {user.id} уже оставил отзыв на магазин")
            return None
        
        # Обеспечиваем значения по умолчанию для данных пользователя
        first_name = user.first_name or "Пользователь"
        last_name = user.last_name or ""
        email = user.email or f"user{user.id}@example.com"
        
        # Если отзыв анонимный, изменяем имя и фамилию
        if review_data.is_anonymous:
            first_name = "Пользователь скрыл свои данные"
            last_name = ""
        
        # Создаем отзыв
        review = ReviewModel(
            user_id=user.id,
            rating=review_data.rating,
            content=review_data.content,
            review_type=ReviewTypeEnum.STORE.value,
            user_first_name=first_name,
            user_last_name=last_name,
            user_email=email,
            is_anonymous=review_data.is_anonymous
        )
        session.add(review)
        await session.commit()
        await session.refresh(review)
        
        # Инвалидируем кэш
        await invalidate_store_reviews_cache()
        await invalidate_user_reviews_cache(user.id)
        
        logger.info(f"Создан отзыв на магазин: user_id={user.id}, rating={review_data.rating}")
        return review
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при создании отзыва на магазин: {str(e)}")
        return None

async def get_review_by_id(
    session: AsyncSession,
    review_id: int,
    include_hidden: bool = False
) -> Optional[ReviewModel]:
    """
    Получение отзыва по ID
    
    Args:
        session: Сессия базы данных
        review_id: ID отзыва
        include_hidden: Включать ли скрытые отзывы
        
    Returns:
        ReviewModel: Отзыв или None, если отзыв не найден
    """
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['review']}{review_id}"
        cached_data = await cache_get(cache_key)
        if cached_data:
            logger.debug(f"Отзыв {review_id} получен из кэша")
            # Десериализуем данные
            return ReviewRead.model_validate(cached_data).model_dump()
        
        # Если в кэше нет, получаем из БД
        review = await ReviewModel.get_by_id(session, review_id)
        
        # Проверяем видимость отзыва
        if review and (include_hidden or not review.is_hidden):
            # Кэшируем результат
            review_data = ReviewRead.from_orm_with_stats(review).model_dump()
            await cache_set(cache_key, review_data, CACHE_TTL["review"])
            return review
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении отзыва по ID {review_id}: {str(e)}")
        return None

async def get_product_reviews(
    session: AsyncSession,
    product_id: int,
    page: int = 1,
    limit: int = 10,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """
    Получение отзывов для товара
    
    Args:
        session: Сессия базы данных
        product_id: ID товара
        page: Номер страницы
        limit: Количество записей на странице
        include_hidden: Включать ли скрытые отзывы
        
    Returns:
        Dict: Пагинированный результат с отзывами
    """
    try:
        # Формируем ключ кэша с учетом параметра include_hidden
        cache_key = f"{CACHE_KEYS['product_reviews']}{product_id}:{page}:{limit}:{include_hidden}"
        logger.debug(f"Проверяем кэш для отзывов товара {product_id} с ключом {cache_key}")
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.info(f"Отзывы для товара {product_id} (страница {page}, лимит {limit}, include_hidden={include_hidden}) получены из кэша")
            return cached_data
        
        # Если данных в кэше нет, получаем из БД
        logger.info(f"Получаем отзывы для товара {product_id} из БД, страница {page}, лимит {limit}, include_hidden={include_hidden}")
        
        # Получаем отзывы из БД
        reviews, total = await ReviewModel.get_by_product_id(
            session, product_id, page, limit, include_hidden
        )
        
        # Логируем результат
        logger.info(f"Получено {len(reviews)} отзывов из {total} для товара {product_id}")
        
        # Преобразуем в модель ответа
        result = {
            "items": [ReviewRead.from_orm_with_stats(review).model_dump() for review in reviews],
            "total": total,
            "page": page,
            "size": limit,
            "pages": ceil(total / limit) if total > 0 else 1
        }
        
        # Кэшируем результат
        logger.debug(f"Сохраняем отзывы товара {product_id} в кэш с ключом {cache_key}")
        # Определяем TTL в зависимости от типа запроса
        ttl = CACHE_TTL["reviews"] if not include_hidden else CACHE_TTL["reviews"] // 2  # Для админов кэш хранится меньше
        await cache_set(cache_key, result, ttl)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении отзывов для товара {product_id}: {str(e)}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "size": limit,
            "pages": 1
        }

async def get_store_reviews(
    session: AsyncSession,
    page: int = 1,
    limit: int = 10,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """
    Получение отзывов для магазина
    
    Args:
        session: Сессия базы данных
        page: Номер страницы
        limit: Количество записей на странице
        include_hidden: Включать ли скрытые отзывы
        
    Returns:
        Dict: Пагинированный результат с отзывами
    """
    try:
        # Формируем ключ кэша с учетом параметра include_hidden
        cache_key = f"{CACHE_KEYS['store_reviews']}{page}:{limit}:{include_hidden}"
        logger.debug(f"Проверяем кэш для отзывов магазина с ключом {cache_key}")
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.info(f"Отзывы для магазина (страница {page}, лимит {limit}, include_hidden={include_hidden}) получены из кэша")
            return cached_data
        
        # Если данных в кэше нет, получаем из БД
        logger.info(f"Получаем отзывы для магазина из БД, страница {page}, лимит {limit}, include_hidden={include_hidden}")
        
        # Получаем отзывы из БД
        reviews, total = await ReviewModel.get_store_reviews(
            session, page, limit, include_hidden
        )
        
        # Логируем результат
        logger.info(f"Получено {len(reviews)} отзывов из {total} для магазина")
        
        # Преобразуем в модель ответа
        result = {
            "items": [ReviewRead.from_orm_with_stats(review).model_dump() for review in reviews],
            "total": total,
            "page": page,
            "size": limit,
            "pages": ceil(total / limit) if total > 0 else 1
        }
        
        # Кэшируем результат
        logger.debug(f"Сохраняем отзывы магазина в кэш с ключом {cache_key}")
        # Определяем TTL в зависимости от типа запроса
        ttl = CACHE_TTL["reviews"] if not include_hidden else CACHE_TTL["reviews"] // 2  # Для админов кэш хранится меньше
        await cache_set(cache_key, result, ttl)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении отзывов для магазина: {str(e)}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "size": limit,
            "pages": 1
        }

async def create_admin_comment(
    session: AsyncSession,
    admin: User,
    comment_data: AdminCommentCreate
) -> Optional[AdminCommentModel]:
    """
    Создание комментария администратора к отзыву
    
    Args:
        session: Сессия базы данных
        admin: Администратор
        comment_data: Данные комментария
        
    Returns:
        AdminCommentModel: Созданный комментарий или None в случае ошибки
    """
    try:
        # Проверяем существование отзыва
        review = await ReviewModel.get_by_id(session, comment_data.review_id)
        if not review:
            logger.warning(f"Отзыв с ID {comment_data.review_id} не найден")
            return None
        
        # Создаем имя администратора из first_name и last_name
        admin_name = f"{admin.first_name or ''} {admin.last_name or ''}".strip()
        if not admin_name:
            admin_name = f"Администратор #{admin.id}"
        
        # Создаем комментарий
        comment = AdminCommentModel(
            review_id=comment_data.review_id,
            admin_user_id=admin.id,
            content=comment_data.content,
            admin_name=admin_name
        )
        session.add(comment)
        await session.commit()
        await session.refresh(comment)
        
        # Инвалидируем кэш в отдельном блоке try
        try:
            await invalidate_review_cache(comment_data.review_id)
            if review.review_type == ReviewTypeEnum.PRODUCT.value and review.product_id:
                await invalidate_product_reviews_cache(review.product_id)
            elif review.review_type == ReviewTypeEnum.STORE.value:
                await invalidate_store_reviews_cache()
        except Exception as cache_error:
            # Логируем ошибку кэша, но не откатываем транзакцию БД
            logger.error(f"Ошибка при инвалидации кэша после добавления комментария к отзыву {comment_data.review_id}: {str(cache_error)}")
        
        logger.info(f"Создан комментарий администратора к отзыву {comment_data.review_id}")
        return comment
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при создании комментария администратора: {str(e)}")
        return None

async def toggle_review_visibility(
    session: AsyncSession,
    review_id: int,
    is_hidden: bool
) -> Optional[Dict[str, Any]]:
    """
    Изменение видимости отзыва
    
    Args:
        session: Сессия базы данных
        review_id: ID отзыва
        is_hidden: Скрыть отзыв (True) или показать (False)
        
    Returns:
        Dict[str, Any]: Словарь с данными обновленного отзыва или None в случае ошибки
    """
    try:
        # Получаем отзыв
        review = await ReviewModel.get_by_id(session, review_id)
        if not review:
            logger.warning(f"Отзыв с ID {review_id} не найден")
            return None
        
        # Сохраняем все необходимые данные до обновления
        review_data = {
            "id": review.id,
            "user_id": review.user_id,
            "rating": review.rating,
            "content": review.content,
            "review_type": review.review_type,
            "product_id": review.product_id,
            "product_name": review.product_name,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "is_hidden": is_hidden,  # Новое значение
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
        
        # Обновляем видимость отзыва
        review.is_hidden = is_hidden
        
        # Сначала фиксируем изменения в базе данных 
        await session.commit()
        
        # После успешного коммита в отдельном блоке try инвалидируем кэш
        try:
            await invalidate_review_cache(review_id)
            if review.review_type == ReviewTypeEnum.PRODUCT.value and review.product_id:
                await invalidate_product_reviews_cache(review.product_id)
            elif review.review_type == ReviewTypeEnum.STORE.value:
                await invalidate_store_reviews_cache()
        except Exception as cache_error:
            # Логируем ошибку кэша, но не откатываем транзакцию БД
            logger.error(f"Ошибка при инвалидации кэша для отзыва {review_id}: {str(cache_error)}")
        
        logger.info(f"Изменена видимость отзыва {review_id}: is_hidden={is_hidden}")
        return review_data  # Возвращаем словарь вместо объекта ORM
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при изменении видимости отзыва {review_id}: {str(e)}")
        return None

async def add_review_reaction(
    session: AsyncSession,
    user: User,
    reaction_data: ReactionCreate
) -> Optional[ReviewReactionModel]:
    """
    Добавление реакции на отзыв
    
    Args:
        session: Сессия базы данных
        user: Пользователь
        reaction_data: Данные реакции
        
    Returns:
        ReviewReactionModel: Созданная реакция или None в случае ошибки
    """
    try:
        # Проверяем существование отзыва
        review = await ReviewModel.get_by_id(session, reaction_data.review_id)
        if not review:
            logger.warning(f"Отзыв с ID {reaction_data.review_id} не найден")
            return None
        
        # Проверяем, не оставил ли пользователь уже реакцию на этот отзыв
        existing_reaction = await ReviewReactionModel.get_user_reaction(
            session, reaction_data.review_id, user.id
        )
        
        if existing_reaction:
            # Если реакция уже существует и совпадает с новой, удаляем её (отмена реакции)
            if existing_reaction.reaction_type == reaction_data.reaction_type.value:
                await session.delete(existing_reaction)
                await session.commit()
                
                # Инвалидируем кэш в отдельном блоке
                try:
                    await invalidate_review_cache(reaction_data.review_id)
                except Exception as cache_error:
                    logger.error(f"Ошибка при инвалидации кэша для отзыва {reaction_data.review_id}: {str(cache_error)}")
                
                logger.info(f"Удалена реакция пользователя {user.id} на отзыв {reaction_data.review_id}")
                return None
            
            # Если реакция существует, но отличается от новой, обновляем её
            existing_reaction.reaction_type = reaction_data.reaction_type.value
            await session.commit()
            
            # Инвалидируем кэш в отдельном блоке
            try:
                await invalidate_review_cache(reaction_data.review_id)
            except Exception as cache_error:
                logger.error(f"Ошибка при инвалидации кэша для отзыва {reaction_data.review_id}: {str(cache_error)}")
            
            logger.info(f"Обновлена реакция пользователя {user.id} на отзыв {reaction_data.review_id}: {reaction_data.reaction_type.value}")
            return existing_reaction
        
        # Создаем новую реакцию
        reaction = ReviewReactionModel(
            review_id=reaction_data.review_id,
            user_id=user.id,
            reaction_type=reaction_data.reaction_type.value
        )
        session.add(reaction)
        await session.commit()
        await session.refresh(reaction)
        
        # Инвалидируем кэш в отдельном блоке
        try:
            await invalidate_review_cache(reaction_data.review_id)
        except Exception as cache_error:
            logger.error(f"Ошибка при инвалидации кэша для отзыва {reaction_data.review_id}: {str(cache_error)}")
        
        logger.info(f"Создана реакция пользователя {user.id} на отзыв {reaction_data.review_id}: {reaction_data.reaction_type.value}")
        return reaction
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка при добавлении реакции на отзыв: {str(e)}")
        return None

async def get_product_review_stats(
    session: AsyncSession,
    product_id: int
) -> ReviewStats:
    """
    Получение статистики отзывов о товаре
    
    Args:
        session: Сессия базы данных
        product_id: ID товара
        
    Returns:
        ReviewStats: Статистика отзывов
    """
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['product_statistics']}{product_id}"
        cached_data = await cache_get(cache_key)
        if cached_data:
            logger.debug(f"Статистика отзывов для товара {product_id} получена из кэша")
            return cached_data
        
        # Получаем средний рейтинг
        avg_rating = await ReviewModel.get_product_avg_rating(session, product_id)
        
        # Получаем количество отзывов по каждому рейтингу (1-5)
        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # Выполняем запрос к БД для получения количества отзывов по каждому рейтингу
        for rating in range(1, 6):
            query = text(f"""
                SELECT COUNT(*) FROM reviews 
                WHERE product_id = {product_id} 
                AND review_type = '{ReviewTypeEnum.PRODUCT.value}' 
                AND rating = {rating}
                AND is_hidden = FALSE
            """)
            result = await session.execute(query)
            count = result.scalar_one()
            rating_counts[rating] = count
        
        # Вычисляем общее количество отзывов
        total_reviews = sum(rating_counts.values())
        
        # Формируем ответ
        stats = {
            "average_rating": avg_rating,
            "total_reviews": total_reviews,
            "rating_counts": rating_counts
        }
        
        # Кэшируем результат
        await cache_set(cache_key, stats, CACHE_TTL["statistics"])
        
        return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики отзывов о товаре {product_id}: {str(e)}")
        return {
            "average_rating": 0.0,
            "total_reviews": 0,
            "rating_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }

async def get_batch_product_review_stats(
    session: AsyncSession,
    product_ids: List[int]
) -> Dict[str, Any]:
    """
    Пакетное получение статистики отзывов для нескольких товаров
    
    Args:
        session: Сессия базы данных
        product_ids: Список ID товаров
        
    Returns:
        Dict[str, Any]: Словарь со статистикой отзывов для каждого товара
    """
    try:
        logger.info(f"Запрос пакетной статистики отзывов для товаров: {product_ids}")
        
        # Проверяем кэш для всего пакета
        cache_key = f"{CACHE_KEYS['product_batch_statistics']}{','.join(map(str, sorted(product_ids)))}"
        cached_data = await cache_get(cache_key)
        
        if cached_data:
            logger.debug(f"Пакетная статистика отзывов получена из кэша для {len(product_ids)} товаров")
            return cached_data
            
        # Результирующий словарь
        results = {}
        
        if not product_ids:
            return results
            
        # Преобразуем список ID в строку для SQL запроса
        product_ids_str = ','.join(str(pid) for pid in product_ids)
        
        # Для оптимизации делаем один запрос за всеми средними рейтингами
        avg_ratings_query = text("""
            SELECT product_id, AVG(rating) as avg_rating
            FROM reviews
            WHERE review_type = 'product'
            AND is_hidden = FALSE
            AND product_id IN :ids
            GROUP BY product_id
        """).bindparams(bindparam("ids", expanding=True))
        avg_ratings_result = await session.execute(avg_ratings_query, {"ids": product_ids})
        avg_ratings = {str(row[0]): float(row[1]) for row in avg_ratings_result}
        
        # Запрос для получения количества отзывов по каждому рейтингу для всех товаров
        rating_counts_query = text("""
            SELECT product_id, rating, COUNT(*) as count
            FROM reviews
            WHERE review_type = 'product'
            AND is_hidden = FALSE
            AND product_id IN :ids
            GROUP BY product_id, rating
        """).bindparams(bindparam("ids", expanding=True))
        rating_counts_result = await session.execute(rating_counts_query, {"ids": product_ids})
        
        # Инициализируем словарь для подсчета рейтингов по каждому товару
        product_rating_counts = {str(pid): {1: 0, 2: 0, 3: 0, 4: 0, 5: 0} for pid in product_ids}
        
        # Заполняем словарь данными из запроса
        for row in rating_counts_result:
            product_id, rating, count = str(row[0]), row[1], row[2]
            product_rating_counts[product_id][rating] = count
        
        # Формируем результат для каждого товара
        for product_id in product_ids:
            pid_str = str(product_id)
            
            # Если в базе нет данных о товаре, устанавливаем средний рейтинг 0
            if pid_str not in avg_ratings:
                avg_rating = 0.0
            else:
                avg_rating = avg_ratings[pid_str]
                
            rating_counts = product_rating_counts.get(pid_str, {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
            total_reviews = sum(rating_counts.values())
            
            # Формируем статистику для данного товара
            results[pid_str] = {
                "average_rating": round(avg_rating, 1),
                "total_reviews": total_reviews,
                "rating_counts": rating_counts
            }
        
        # Кэшируем результат
        await cache_set(cache_key, results, CACHE_TTL["statistics"])
        
        return results
    except Exception as e:
        logger.error(f"Ошибка при пакетном получении статистики отзывов: {str(e)}")
        # Возвращаем пустую статистику для каждого товара в случае ошибки
        return {
            str(product_id): {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            } for product_id in product_ids
        }

async def get_store_review_stats(
    session: AsyncSession,
) -> ReviewStats:
    """
    Получение статистики отзывов о магазине
    
    Args:
        session: Сессия базы данных
        
    Returns:
        ReviewStats: Статистика отзывов
    """
    try:
        # Проверяем кэш
        cache_key = f"{CACHE_KEYS['store_review_stats']}"
        cached_data = await cache_get(cache_key)
        if cached_data:
            logger.debug(f"Статистика отзывов о магазине получена из кэша")
            return cached_data
        
        # Получаем средний рейтинг из БД
        avg_rating = await ReviewModel.get_store_avg_rating(session)
        
        # Получаем общее количество отзывов
        total_query = await session.execute(
            select(func.count()).where(
                ReviewModel.review_type == ReviewTypeEnum.STORE.value,
                ReviewModel.is_hidden == False
            )
        )
        total_reviews = total_query.scalar() or 0
        
        # Получаем распределение рейтингов
        rating_counts = {}
        for rating in range(1, 6):
            count_query = await session.execute(
                select(func.count()).where(
                    ReviewModel.review_type == ReviewTypeEnum.STORE.value,
                    ReviewModel.rating == rating,
                    ReviewModel.is_hidden == False
                )
            )
            count = count_query.scalar() or 0
            rating_counts[rating] = count
        
        # Формируем результат
        result = {
            "average_rating": round(avg_rating, 1),
            "total_reviews": total_reviews,
            "rating_counts": rating_counts
        }
        
        # Кэшируем результат
        await cache_set(cache_key, result, CACHE_TTL["stats"])
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении статистики отзывов о магазине: {str(e)}")
        return {
            "average_rating": 0.0,
            "total_reviews": 0,
            "rating_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        } 