"""Модуль для управления пользовательскими сессиями и их жизненным циклом."""

import logging
from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models import UserSessionModel
from .cache_service import cache_service, cached, USER_CACHE_TTL

logger = logging.getLogger(__name__)

class SessionService:
    """Сервис для работы с пользовательскими сессиями"""
    
    @staticmethod
    async def create_session(
        session: AsyncSession,
        user_id: int,
        jti: str,
        user_agent: str = None,
        ip_address: str = None,
        expires_at: datetime = None
    ) -> UserSessionModel:
        """
        Создает новую сессию пользователя
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            jti: Уникальный идентификатор JWT токена
            user_agent: User-Agent браузера
            ip_address: IP-адрес пользователя
            expires_at: Время истечения токена
            
        Returns:
            UserSessionModel: Созданная сессия
        """
        try:
            # Создаем запись о сессии
            new_session = UserSessionModel(
                user_id=user_id,
                jti=jti,
                user_agent=user_agent,
                ip_address=ip_address,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at
            )
            
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)
            
            # Инвалидируем кэш сессий пользователя
            cache_key = f"get_user_sessions:{user_id}"
            await cache_service.delete(cache_key)
            
            return new_session
        except SQLAlchemyError as e:
            logger.error("Ошибка при создании сессии: %s", str(e))
            raise
    
    @staticmethod
    @cached(ttl=USER_CACHE_TTL)
    async def get_user_sessions(session: AsyncSession, user_id: int, active_only: bool = True) -> List[UserSessionModel]:
        """
        Получает список сессий пользователя
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            active_only: Только активные сессии
            
        Returns:
            List[UserSessionModel]: Список сессий
        """
        try:
            query = select(UserSessionModel).filter(UserSessionModel.user_id == user_id)
            
            if active_only:
                query = query.filter(UserSessionModel.is_active is True)
                
            query = query.order_by(UserSessionModel.created_at.desc())
            
            result = await session.execute(query)
            sessions = result.scalars().all()
            
            return sessions
        except SQLAlchemyError as e:
            logger.error("Ошибка при получении сессий пользователя: %s", str(e))
            return []
    
    @staticmethod
    async def revoke_session(session: AsyncSession, session_id: int, user_id: int = None, reason: str = "Manual revoke") -> bool:
        """
        Отзывает сессию пользователя
        
        Args:
            session: Сессия базы данных
            session_id: ID сессии
            user_id: ID пользователя (для проверки прав)
            reason: Причина отзыва
            
        Returns:
            bool: True, если сессия успешно отозвана
        """
        try:
            query = select(UserSessionModel).filter(UserSessionModel.id == session_id)
            
            # Если указан ID пользователя, проверяем права
            if user_id is not None:
                query = query.filter(UserSessionModel.user_id == user_id)
                
            result = await session.execute(query)
            user_session = result.scalars().first()
            
            if not user_session:
                logger.warning("Сессия %s не найдена или не принадлежит пользователю %s", session_id, user_id)
                return False
            
            # Отзываем сессию
            user_session.is_active = False
            user_session.revoked_at = datetime.now(timezone.utc)
            user_session.revoked_reason = reason
            
            await session.commit()
            
            # Инвалидируем кэш сессий пользователя
            cache_key = f"get_user_sessions:{user_session.user_id}"
            await cache_service.delete(cache_key)
            
            return True
        except SQLAlchemyError as e:
            logger.error("Ошибка при отзыве сессии: %s", str(e))
            return False
    
    @staticmethod
    async def revoke_session_by_jti(session: AsyncSession, jti: str, reason: str = "Token revoked") -> bool:
        """
        Отзывает сессию по JTI токена
        
        Args:
            session: Сессия базы данных
            jti: JTI токена
            reason: Причина отзыва
            
        Returns:
            bool: True, если сессия успешно отозвана
        """
        try:
            query = select(UserSessionModel).filter(
                UserSessionModel.jti == jti,
                UserSessionModel.is_active is True
            )
            
            result = await session.execute(query)
            user_session = result.scalars().first()
            
            if not user_session:
                logger.warning("Активная сессия с JTI %s не найдена", jti)
                return False
            
            # Отзываем сессию
            user_session.is_active = False
            user_session.revoked_at = datetime.now(timezone.utc)
            user_session.revoked_reason = reason
            
            await session.commit()
            
            # Инвалидируем кэш сессий пользователя
            cache_key = f"get_user_sessions:{user_session.user_id}"
            await cache_service.delete(cache_key)
            
            return True
        except SQLAlchemyError as e:
            logger.error("Ошибка при отзыве сессии по JTI: %s", str(e))
            return False
    
    @staticmethod
    async def revoke_all_user_sessions(session: AsyncSession, user_id: int, exclude_jti: str = None, reason: str = "All sessions revoked") -> int:
        """
        Отзывает все активные сессии пользователя, кроме указанной
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            exclude_jti: JTI токена, который не нужно отзывать
            reason: Причина отзыва
            
        Returns:
            int: Количество отозванных сессий
        """
        try:
            # Получаем все активные сессии пользователя
            query = select(UserSessionModel).filter(
                UserSessionModel.user_id == user_id,
                UserSessionModel.is_active is True
            )
            
            if exclude_jti:
                query = query.filter(UserSessionModel.jti != exclude_jti)
                
            result = await session.execute(query)
            sessions = result.scalars().all()
            
            revoke_count = 0
            
            # Отзываем каждую сессию
            for user_session in sessions:
                user_session.is_active = False
                user_session.revoked_at = datetime.now(timezone.utc)
                user_session.revoked_reason = reason
                revoke_count += 1
            
            if revoke_count > 0:
                await session.commit()
                
                # Инвалидируем кэш сессий пользователя
                cache_key = f"get_user_sessions:{user_id}"
                await cache_service.delete(cache_key)
            
            return revoke_count
        except SQLAlchemyError as e:
            logger.error("Ошибка при отзыве всех сессий пользователя: %s", str(e))
            return 0
    
    @staticmethod
    async def cleanup_expired_sessions(session: AsyncSession) -> int:
        """
        Очищает просроченные сессии из базы данных
        
        Args:
            session: Сессия базы данных
            
        Returns:
            int: Количество удаленных сессий
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Помечаем как неактивные сессии с истекшим сроком
            query = select(UserSessionModel).filter(
                UserSessionModel.is_active is True,
                UserSessionModel.expires_at < now
            )
            
            result = await session.execute(query)
            expired_sessions = result.scalars().all()
            
            count = 0
            for user_session in expired_sessions:
                user_session.is_active = False
                user_session.revoked_at = now
                user_session.revoked_reason = "Token expired"
                count += 1
            
            if count > 0:
                await session.commit()
                logger.info("Деактивировано %d просроченных сессий", count)
            
            return count
        except SQLAlchemyError as e:
            logger.error("Ошибка при очистке просроченных сессий: %s", str(e))
            return 0
    
    @staticmethod
    async def is_session_active(session: AsyncSession, jti: str) -> bool:
        """
        Проверяет, активна ли сессия с указанным JTI
        
        Args:
            session: Сессия базы данных
            jti: JTI токена
            
        Returns:
            bool: True, если сессия активна
        """
        try:
            query = select(UserSessionModel).filter(
                UserSessionModel.jti == jti,
                UserSessionModel.is_active is True
            )
            
            result = await session.execute(query)
            user_session = result.scalars().first()
            
            return user_session is not None
        except SQLAlchemyError as e:
            logger.error("Ошибка при проверке активности сессии: %s", str(e))
            return False

# Создаем глобальный экземпляр сервиса для использования в приложении
session_service = SessionService() 
