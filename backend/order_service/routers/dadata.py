from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import httpx
import os
import logging
logger = logging.getLogger("dadata_router")
DADATA_CACHE_TTL = int(os.getenv("DADATA_CACHE_TTL", "86400"))  # TTL сутки
import json
import hashlib
from cache import get_cached_data, set_cached_data

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
    query: str = Field(..., description="Строка для подсказки")
    from_bound: dict = Field(None, example={"value": "city"})
    to_bound: dict = Field(None, example={"value": "city"})
    locations: list = Field(None, description="Фильтры местоположения")

@router.post("/address", summary="Proxy DaData address suggest")
async def suggest_address(body: SuggestRequest):
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    payload = body.model_dump(exclude_none=True)
    # кэш DaData address (24h TTL)
    key = f"dadata:address:{hashlib.md5(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()}"
    logger.info(f"Проверяю кэш подсказок адресов, ключ={key}")
    cached = await get_cached_data(key)
    if cached:
        logger.info(f"Попадание в кэш подсказок адресов, ключ={key}")
        return cached
    logger.info(f"Промах кэша подсказок адресов, ключ={key}, отправляю запрос к API")
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=payload, headers=HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    await set_cached_data(key, data, DADATA_CACHE_TTL)
    logger.info(f"Сохраняю в кэш подсказки адресов, ключ={key}, ttl={DADATA_CACHE_TTL}")
    return data

@router.post("/fio", summary="Proxy DaData FIO suggest")
async def suggest_fio(body: dict):
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/fio"
    # кэш DaData fio
    query = body.get("query", "")
    key = f"dadata:fio:{hashlib.md5(query.encode('utf-8')).hexdigest()}"
    logger.info(f"Проверяю кэш подсказок ФИО, ключ={key}")
    cached = await get_cached_data(key)
    if cached:
        logger.info(f"Попадание в кэш подсказок ФИО, ключ={key}")
        return cached
    logger.info(f"Промах кэша подсказок ФИО, ключ={key}, отправляю запрос к API")
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=body, headers=HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    await set_cached_data(key, data, DADATA_CACHE_TTL)
    logger.info(f"Сохраняю в кэш подсказки ФИО, ключ={key}, ttl={DADATA_CACHE_TTL}")
    return data 