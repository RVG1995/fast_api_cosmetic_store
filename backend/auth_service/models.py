from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    hashed_password: Mapped[str]  = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
    activation_token: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)

    is_user: Mapped[bool] = mapped_column(default=True, server_default=text('true'), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
    
    extend_existing = True

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
    
    async def activate(self, session: AsyncSession) -> None:
        """Активировать пользователя и удалить токен активации"""
        self.is_active = True
        self.activation_token = None
        await session.commit()
    
