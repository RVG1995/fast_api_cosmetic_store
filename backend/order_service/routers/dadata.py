from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import httpx
import os

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
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=payload, headers=HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

@router.post("/fio", summary="Proxy DaData FIO suggest")
async def suggest_fio(body: dict):
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/fio"
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(url, json=body, headers=HEADERS)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json() 