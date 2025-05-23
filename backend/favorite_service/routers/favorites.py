from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Favorite
from schema import FavoriteIn, FavoriteOut
from database import get_async_session
from app.services.auth import get_current_user_id
from cache import cache_service, DEFAULT_CACHE_TTL
import hashlib

router = APIRouter(prefix="/favorites", tags=["favorites"])

def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    raw = prefix + ":" + ":".join(map(str, args)) + ":" + ":".join(f"{k}={v}" for k,v in kwargs.items())
    return "favorites:" + hashlib.md5(raw.encode()).hexdigest()

@router.post("/", response_model=FavoriteOut)
async def add_favorite(
    favorite: FavoriteIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    q = await session.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.product_id == favorite.product_id)
    )
    if q.scalar():
        raise HTTPException(status_code=400, detail="Already in favorites")
    fav = Favorite(user_id=user_id, product_id=favorite.product_id)
    session.add(fav)
    await session.commit()
    await session.refresh(fav)
    # Инвалидируем кэш пользователя
    await cache_service.delete(_make_cache_key("list", user_id))
    return fav

@router.delete("/{product_id}", status_code=204)
async def remove_favorite(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    q = await session.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.product_id == product_id)
    )
    fav = q.scalar()
    if not fav:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(fav)
    await session.commit()
    await cache_service.delete(_make_cache_key("list", user_id))

@router.get("/", response_model=list[FavoriteOut])
async def list_favorites(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    cache_key = _make_cache_key("list", user_id)
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return cached
    q = await session.execute(select(Favorite).where(Favorite.user_id == user_id))
    result = q.scalars().all()
    data = [FavoriteOut.model_validate(fav).model_dump() for fav in result]
    await cache_service.set(cache_key, data, ttl=DEFAULT_CACHE_TTL)
    return data 