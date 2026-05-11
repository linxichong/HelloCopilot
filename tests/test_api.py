import pytest
from fastapi import HTTPException

from app.main import create_item, get_item, health, list_items
from app.schemas import ItemCreate


def test_health_check_is_public() -> None:
    assert health() == {"status": "ok"}


def test_create_list_and_get_item(db_session, current_user) -> None:
    created = create_item(
        ItemCreate(
            name="demo item",
            name2="secondary name",
            description="created from test",
            age=7,
        ),
        db_session,
        current_user,
    )

    assert created.id == 1
    assert created.name == "demo item"
    assert created.name2 == "secondary name"
    assert created.description == "created from test"
    assert created.age == 7
    assert created.created_at

    items = list_items(db_session, current_user)
    assert [item.id for item in items] == [1]

    found = get_item(1, db_session, current_user)
    assert found.name == "demo item"


def test_get_missing_item_returns_404(db_session, current_user) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_item(404, db_session, current_user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Item not found"
