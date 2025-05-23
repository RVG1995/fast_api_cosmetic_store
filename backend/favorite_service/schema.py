from pydantic import BaseModel
from datetime import datetime

class FavoriteIn(BaseModel):
    product_id: int

class FavoriteOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True 