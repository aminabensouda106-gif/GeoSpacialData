from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from platform_api.auth import optional_user
from platform_api.cube_client import cube_load, cube_meta
from platform_api.datasets import (
    geocode,
    get_dataset,
    get_dataset_registry,
    get_lineage,
    get_preview,
    nearby_datasets,
    search_datasets,
    terria_link,
)

app = FastAPI(
    title="GeoSpacialData BFF",
    description="Backend-for-frontend serving the Portal and bridging Cube, STAC, and Keycloak",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
async def search(
    q: Annotated[str, Query(description="Search query over dataset titles and descriptions")],
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> list[dict[str, Any]]:
    if not q.strip():
        return get_dataset_registry()
    return search_datasets(q)


@app.get("/datasets/{dataset_id}")
async def dataset_detail(
    dataset_id: str,
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> dict[str, Any]:
    ds = get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"dataset {dataset_id!r} not found")
    return ds


@app.get("/datasets/{dataset_id}/lineage")
async def dataset_lineage(
    dataset_id: str,
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> list[dict[str, Any]]:
    ds = get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"dataset {dataset_id!r} not found")
    return get_lineage(dataset_id)


@app.get("/datasets/{dataset_id}/preview")
async def dataset_preview(
    dataset_id: str,
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> dict[str, Any]:
    ds = get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"dataset {dataset_id!r} not found")
    return get_preview(dataset_id)


@app.post("/export")
async def export_data(
    body: dict[str, Any],
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> dict[str, Any]:
    cube_query = body.get("query")
    if not cube_query:
        raise HTTPException(status_code=400, detail="missing 'query' in request body")
    result = await cube_load(cube_query)
    return result


@app.get("/datasets/{dataset_id}/terria-link")
async def dataset_terria_link(
    dataset_id: str,
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> dict[str, Any]:
    ds = get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail=f"dataset {dataset_id!r} not found")
    link = terria_link(dataset_id)
    if link is None:
        raise HTTPException(status_code=404, detail=f"no TerriaMap link for {dataset_id!r}")
    return {"terria_link": link}


@app.get("/geocode")
async def geocode_place(
    q: Annotated[str, Query(description="Place name to geocode, e.g. a Moroccan city")],
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> dict[str, Any]:
    result = await geocode(q)
    if result is None:
        raise HTTPException(status_code=404, detail=f"no geocoding result for {q!r}")
    return result


@app.get("/nearby")
async def nearby(
    lat: Annotated[float, Query(description="Latitude of the search point")],
    lon: Annotated[float, Query(description="Longitude of the search point")],
    radius_km: Annotated[float, Query(description="Search radius in kilometres")] = 100.0,
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> list[dict[str, Any]]:
    return nearby_datasets(lat, lon, radius_km)


@app.get("/meta")
async def meta(
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> dict[str, Any]:
    return await cube_meta()
