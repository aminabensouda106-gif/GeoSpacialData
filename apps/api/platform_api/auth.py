from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from platform_api.config import keycloak_issuer, keycloak_jwks_url

_bearer = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        resp = httpx.get(keycloak_jwks_url(), timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _decode_token(token: str) -> dict:
    jwks = _get_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    key = None
    for k in jwks.get("keys", []):
        if k["kid"] == header.get("kid"):
            key = k
            break
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="signing key not found"
        )

    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=keycloak_issuer(),
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict | None:
    if creds is None:
        return None
    return _decode_token(creds.credentials)


async def require_user(
    user: Annotated[dict | None, Depends(optional_user)],
) -> dict:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    return user
