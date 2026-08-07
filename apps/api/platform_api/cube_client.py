from __future__ import annotations

import time
from typing import Any

import httpx
from jose import jwt

from platform_api.config import cube_api_secret, cube_api_url


def _cube_token() -> str:
    payload = {"iat": int(time.time())}
    return jwt.encode(payload, cube_api_secret(), algorithm="HS256")


async def cube_load(query: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{cube_api_url()}/load",
            json={"query": query},
            headers={"Authorization": _cube_token()},
        )
        resp.raise_for_status()
        return resp.json()


async def cube_meta() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{cube_api_url()}/meta",
            headers={"Authorization": _cube_token()},
        )
        resp.raise_for_status()
        return resp.json()
