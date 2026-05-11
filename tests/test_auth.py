from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import pytest

from app.auth import _required_groups, _user_from_claims, require_user
from app.config import Settings


def test_require_user_returns_anonymous_when_auth_is_disabled() -> None:
    user = require_user(credentials=None, settings=Settings(auth_enabled=False))

    assert user.sub == "anonymous"
    assert user.username == "anonymous"


def test_require_user_rejects_missing_token_when_auth_is_enabled() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_user(credentials=None, settings=Settings(auth_enabled=True, auth_issuer="http://issuer"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing bearer token"


def test_required_groups_trims_empty_values() -> None:
    settings = Settings(auth_required_groups=" App Users, ,ArgoCD Admins ")

    assert _required_groups(settings) == {"App Users", "ArgoCD Admins"}


def test_user_from_claims_normalizes_groups() -> None:
    user = _user_from_claims(
        {
            "sub": "user-1",
            "preferred_username": "alice",
            "email": "alice@example.com",
            "groups": ["App Users", 123],
        }
    )

    assert user.sub == "user-1"
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.groups == ["App Users", "123"]


def test_require_user_rejects_invalid_token_without_issuer() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-token")

    with pytest.raises(HTTPException) as exc_info:
        require_user(credentials=credentials, settings=Settings(auth_enabled=True, auth_issuer=""))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Authentication is enabled but AUTH_ISSUER is not configured"
