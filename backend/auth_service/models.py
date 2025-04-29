"""Модели для аутентификации и управления пользователями."""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import String, Boolean, DateTime, ForeignKey

class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass

class UserModel(Base):
    """Модель пользователя системы."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    hashed_password: Mapped[str]  = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
    activation_token: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)
    token_created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    reset_token: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)
    reset_token_created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    is_user: Mapped[bool] = mapped_column(default=True, server_default=text('true'), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
    
    extend_existing = True

    # Определяем отношение с сессиями
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"
    
    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str) -> Optional["UserModel"]:
        """Получить пользователя по email"""
        stmt = select(cls).filter(cls.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_activation_token(cls, session: AsyncSession, token: str) -> Optional["UserModel"]:
        """Получить пользователя по токену активации"""
        stmt = select(cls).filter(cls.activation_token == token)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, user_id: int) -> Optional["UserModel"]:
        """Получить пользователя по ID"""
        return await session.get(cls, user_id)
    
    @classmethod
    async def get_by_reset_token(cls, session: AsyncSession, token: str) -> Optional["UserModel"]:
        """Получить пользователя по токену сброса пароля"""
        stmt = select(cls).filter(cls.reset_token == token)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_all_admins(cls, session: AsyncSession) -> List["UserModel"]:
        """Получить всех пользователей с правами администратора или суперадминистратора"""
        stmt = select(cls).filter(
            (cls.is_admin is True) | (cls.is_super_admin is True)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_all_users(cls, session: AsyncSession) -> List["UserModel"]:
        """Получить всех пользователей"""
        stmt = select(cls)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def activate(self, session: AsyncSession) -> None:
        """Активировать пользователя и удалить токен активации"""
        self.is_active = True
        self.activation_token = None
        await session.commit()
    

class UserSessionModel(Base):
    """
    Модель для хранения информации о сессиях пользователей.
    """
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)  # Unique JWT ID
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # Поддерживает IPv6
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Определяем обратное отношение к пользователю
    user: Mapped[Optional["UserModel"]] = relationship("UserModel", back_populates="sessions")
    
    @classmethod
    async def get_by_jti(cls, session: AsyncSession, jti: str) -> Optional["UserSessionModel"]:
        """
        Получает сессию по идентификатору JWT токена.
        """
        query = select(cls).filter(cls.jti == jti)
        result = await session.execute(query)
        return result.scalars().first()
    
    @classmethod
    async def revoke_session(cls, session: AsyncSession, jti: str, reason: str = "User logout") -> bool:
        """
        Отзывает сессию, помечая её как неактивную.
        """
        user_session = await cls.get_by_jti(session, jti)
        if not user_session:
            return False
            
        user_session.is_active = False
        user_session.revoked_at = datetime.now(timezone.utc)
        user_session.revoked_reason = reason
        
        await session.commit()
        return True
    
    @classmethod
    async def revoke_all_user_sessions(cls, session: AsyncSession, user_id: int, exclude_jti: str = None) -> int:
        """
        Отзывает все активные сессии пользователя, кроме указанной (опционально).
        Возвращает количество отозванных сессий.
        """
        query = select(cls).filter(
            cls.user_id == user_id,
            cls.is_active is True
        )
        
        if exclude_jti:
            query = query.filter(cls.jti != exclude_jti)
            
        result = await session.execute(query)
        sessions = result.scalars().all()
        
        revoke_count = 0
        for user_session in sessions:
            user_session.is_active = False
            user_session.revoked_at = datetime.now(timezone.utc)
            user_session.revoked_reason = "Revoked by new login/logout"
            revoke_count += 1
        
        await session.commit()
        return revoke_count
    
