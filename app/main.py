from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, require_user
from app.database import get_db
from app.models import Item
from app.schemas import ItemCreate, ItemRead

app = FastAPI(title="HelloCopilot API")

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[AuthenticatedUser, Depends(require_user)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/ready")
def ready(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from exc
    return {"status": "ready"}


@app.get("/me", response_model=AuthenticatedUser)
def me(current_user: CurrentUser) -> AuthenticatedUser:
    return current_user


@app.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: DbSession, _current_user: CurrentUser) -> Item:
    item = Item(
        name=payload.name,
        name2=payload.name2,
        description=payload.description,
        age=payload.age,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/items", response_model=list[ItemRead])
def list_items(db: DbSession, _current_user: CurrentUser) -> list[Item]:
    statement = select(Item).order_by(Item.created_at.desc(), Item.id.desc())
    return list(db.scalars(statement).all())


@app.get("/items/{item_id}", response_model=ItemRead)
def get_item(item_id: int, db: DbSession, _current_user: CurrentUser) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
