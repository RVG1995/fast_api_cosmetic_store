"""Модуль для работы с API DaData для подсказок адресов и ФИО."""

import os
import json
import hashlib
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx
from cache import get_cached_data, set_cached_data

logger = logging.getLogger("dadata_router")
DADATA_CACHE_TTL = int(os.getenv("DADATA_CACHE_TTL", "86400"))  # TTL сутки

router = APIRouter(
    prefix="/dadata",
    tags=["dadata"],
    responses={400: {"description": "Bad Request"}, 500: {"description": "Server Error"}}
)

DADATA_TOKEN = os.getenv("DADATA_TOKEN")
HEADERS = {
    "Authorization": f"Token {DADATA_TOKEN}",
    "Content-Type": "application/json"
}

class SuggestRequest(BaseModel):
    """Модель запроса для подсказок адресов DaData."""
    query: str = Field(..., description="Строка для подсказки")
    from_bound: dict = Field(None, example={"value": "city"})
    to_bound: dict = Field(None, example={"value": "city"})
    locations: list = Field(None, description="Фильтры местоположения")

def normalize_obj(obj):
    """Нормализует объект для кэширования (приведение к нижнему регистру)."""
    if isinstance(obj, str):
        return obj.strip().lower()
    if isinstance(obj, list):
        return [normalize_obj(i) for i in obj]
    if isinstance(obj, dict):
        return {k: normalize_obj(obj[k]) for k in sorted(obj)}
    return obj

@router.post("/address", summary="Proxy DaData address suggest")
async def suggest_address(body: SuggestRequest):
    """Получает подсказки адресов от DaData API с кэшированием."""
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    payload = body.model_dump(exclude_none=True)
    # нормализуем значения для кэша (без учёта регистра)
    norm = normalize_obj(payload)
    key_str = json.dumps(norm, ensure_ascii=False, sort_keys=True)
    key = f"dadata:address:{hashlib.md5(key_str.encode('utf-8')).hexdigest()}"
    logger.info("Проверяю кэш подсказок адресов, ключ=%s", key)
    cached = await get_cached_data(key)
    if cached:
        logger.info("Попадание в кэш подсказок адресов, ключ=%s", key)
        return cached
    logger.info("Промах кэша подсказок адресов, ключ=%s, отправляю запрос к API", key)
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=payload, headers=HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    await set_cached_data(key, data, DADATA_CACHE_TTL)
    logger.info("Сохраняю в кэш подсказки адресов, ключ=%s, ttl=%s", key, DADATA_CACHE_TTL)
    return data

@router.post("/fio", summary="Proxy DaData FIO suggest")
async def suggest_fio(body: dict):
    """Получает подсказки ФИО от DaData API с кэшированием."""
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/fio"
    # кэш DaData fio с нормализацией регистра
    raw_q = body.get("query", "")
    q_norm = raw_q.strip().lower()
    key = f"dadata:fio:{hashlib.md5(q_norm.encode('utf-8')).hexdigest()}"
    logger.info("Проверяю кэш подсказок ФИО, ключ=%s", key)
    cached = await get_cached_data(key)
    if cached:
        logger.info("Попадание в кэш подсказок ФИО, ключ=%s", key)
        return cached
    logger.info("Промах кэша подсказок ФИО, ключ=%s, отправляю запрос к API", key)
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=body, headers=HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    await set_cached_data(key, data, DADATA_CACHE_TTL)
    logger.info("Сохраняю в кэш подсказки ФИО, ключ=%s, ttl=%s", key, DADATA_CACHE_TTL)
    return data
