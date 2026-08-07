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
    import asyncio

    async with httpx.AsyncClient(timeout=60) as client:
        for _ in range(30):
            resp = await client.post(
                f"{cube_api_url()}/load",
                json={"query": query},
                headers={"Authorization": _cube_token()},
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("error") != "Continue wait":
                return body
            await asyncio.sleep(1)
        return body


async def cube_meta() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{cube_api_url()}/meta",
            headers={"Authorization": _cube_token()},
        )
        resp.raise_for_status()
        return resp.json()
