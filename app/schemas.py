from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class ItemRead(BaseModel):
    id: int
    name: str
    description: str | None
    price: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
