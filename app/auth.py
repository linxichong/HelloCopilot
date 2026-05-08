import json
from functools import lru_cache
from typing import Annotated, Any
from urllib.request import urlopen

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient
from pydantic import BaseModel, Field

from app.config import Settings, get_settings


bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    sub: str
    username: str | None = None
    email: str | None = None
    groups: list[str] = Field(default_factory=list)
    claims: dict[str, Any] = Field(default_factory=dict)


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


@lru_cache
def _discover_jwks_url(issuer: str) -> str:
    config_url = f"{_normalize_url(issuer)}/.well-known/openid-configuration"
    with urlopen(config_url, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
    jwks_uri = data.get("jwks_uri")
    if not jwks_uri:
        raise ValueError("OIDC discovery document does not include jwks_uri")
    return str(jwks_uri)


@lru_cache
def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _get_claims(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.auth_issuer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is enabled but AUTH_ISSUER is not configured",
        )

    try:
        jwks_url = settings.auth_jwks_url or _discover_jwks_url(settings.auth_issuer)
        signing_key = _get_jwk_client(jwks_url).get_signing_key_from_jwt(token)
        audience = settings.auth_audience or None
        algorithms = [item.strip() for item in settings.auth_algorithms.split(",") if item.strip()]
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=algorithms,
            issuer=_normalize_url(settings.auth_issuer) + "/",
            audience=audience,
            options={"verify_aud": audience is not None},
            leeway=30,
        )
    except HTTPException:
        raise
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to validate authentication token",
        ) from exc


def _user_from_claims(claims: dict[str, Any]) -> AuthenticatedUser:
    groups = claims.get("groups") or []
    if not isinstance(groups, list):
        groups = []

    return AuthenticatedUser(
        sub=str(claims.get("sub", "")),
        username=claims.get("preferred_username") or claims.get("name"),
        email=claims.get("email"),
        groups=[str(group) for group in groups],
        claims=claims,
    )


def _required_groups(settings: Settings) -> set[str]:
    return {group.strip() for group in settings.auth_required_groups.split(",") if group.strip()}


def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if not settings.auth_enabled:
        return AuthenticatedUser(sub="anonymous", username="anonymous")

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _user_from_claims(_get_claims(credentials.credentials, settings))
    required_groups = _required_groups(settings)
    if required_groups and not required_groups.intersection(user.groups):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user does not have a required group",
        )
    return user
