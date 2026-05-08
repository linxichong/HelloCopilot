from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    name2: str | None = Field(default=None, max_length=120)
    description: str | None = None
    age: int | None = Field(default=None, ge=0)


class ItemRead(BaseModel):
    id: int
    name: str
    name2: str | None
    description: str | None
    age: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
