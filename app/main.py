from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item
from app.schemas import ItemCreate, ItemRead

app = FastAPI(title="HelloCopilot API")

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: DbSession) -> Item:
    item = Item(
        name=payload.name,
        description=payload.description,
        age=payload.age,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/items", response_model=list[ItemRead])
def list_items(db: DbSession) -> list[Item]:
    statement = select(Item).order_by(Item.created_at.desc(), Item.id.desc())
    return list(db.scalars(statement).all())


@app.get("/items/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: DbSession) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
