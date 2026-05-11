from sqlalchemy.orm import Session

from app.models import Item
from app.schemas import ItemCreate, ItemRead


def test_item_model_can_be_persisted(db_session: Session) -> None:
    item = Item(name="stored item", name2="alias", description="from sqlite", age=3)

    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id == 1
    assert item.name == "stored item"
    assert item.name2 == "alias"
    assert item.description == "from sqlite"
    assert item.age == 3
    assert item.created_at is not None


def test_item_create_schema_validates_values() -> None:
    payload = ItemCreate(name="valid", age=0)

    assert payload.name == "valid"
    assert payload.age == 0


def test_item_read_schema_maps_from_model(db_session: Session) -> None:
    item = Item(name="readable", description=None, age=None)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    serialized = ItemRead.model_validate(item)

    assert serialized.id == 1
    assert serialized.name == "readable"
    assert serialized.name2 is None
    assert serialized.description is None
    assert serialized.age is None
