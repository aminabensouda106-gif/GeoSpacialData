from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from platform_api.config import stac_api_url, titiler_url

_RECIPE_DIRS = [
    "recipes/datasets",
    "recipes/gee",
]


def _repo_root() -> Path:
    return Path(os.environ.get("PLATFORM_REPO_ROOT", "/opt/dagster/app"))


def _load_all_manifests() -> list[dict[str, Any]]:
    manifests = []
    for d in _RECIPE_DIRS:
        recipe_dir = _repo_root() / d
        if not recipe_dir.is_dir():
            continue
        for f in sorted(recipe_dir.glob("*.yaml")):
            with open(f) as fh:
                manifests.append(yaml.safe_load(fh))
    return manifests


_cache: list[dict[str, Any]] | None = None


def get_dataset_registry() -> list[dict[str, Any]]:
    global _cache
    if _cache is not None:
        return _cache

    manifests = _load_all_manifests()
    datasets = []
    for m in manifests:
        ds: dict[str, Any] = {
            "id": m["id"],
            "title": m.get("title", m["id"]),
            "description": m.get("description", ""),
            "source_type": m.get("source", {}).get("type", "unknown"),
            "modality": m.get("target", {}).get("modality", "unknown"),
            "format": m.get("target", {}).get("format", "unknown"),
        }
        gov = m.get("governance", {})
        ds["owner"] = gov.get("owner")
        ds["classification"] = gov.get("classification")
        ds["source_class"] = gov.get("source_class")
        ds["license"] = gov.get("license")
        ds["citation"] = gov.get("citation")
        ds["caveats"] = gov.get("caveats")

        pub = m.get("publish", {})
        ds["stac_collection"] = pub.get("stac_collection")
        ds["terria_group"] = pub.get("terria_group")
        ds["has_pmtiles"] = pub.get("pmtiles", False)

        quality = m.get("quality", {})
        ds["quality_checks"] = quality.get("checks", [])

        datasets.append(ds)

    _cache = datasets
    return datasets


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    for ds in get_dataset_registry():
        if ds["id"] == dataset_id:
            return ds
    return None


def search_datasets(query: str) -> list[dict[str, Any]]:
    q = query.lower()
    results = []
    for ds in get_dataset_registry():
        text = f"{ds['title']} {ds['description']} {ds.get('modality','')} {ds.get('source_type','')} {ds.get('caveats','')}".lower()
        if q in text:
            results.append(ds)
    return results


def get_lineage(dataset_id: str) -> list[dict[str, Any]]:
    try:
        from pyiceberg.catalog import load_catalog

        catalog = load_catalog(
            "lakekeeper",
            **{
                "uri": os.environ.get("LAKEKEEPER_URI", "http://lakekeeper:8181/catalog"),
                "warehouse": os.environ.get("LAKEKEEPER_WAREHOUSE", "poc"),
                "s3.endpoint": os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333"),
                "s3.access-key-id": os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
                "s3.secret-access-key": os.environ.get(
                    "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
                ),
            },
        )
        table = catalog.load_table("platform.pipeline_runs")
        df = table.scan().to_arrow()
        runs = df.filter(df.column("dataset_id") == dataset_id).to_pylist()
        return runs
    except Exception:
        return []


def get_preview(dataset_id: str) -> dict[str, Any]:
    ds = get_dataset(dataset_id)
    if ds is None:
        return {"error": "not found"}

    if ds.get("stac_collection"):
        try:
            resp = httpx.get(
                f"{stac_api_url()}/collections/{ds['stac_collection']}/items",
                params={"limit": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                items = resp.json().get("features", [])
                if items:
                    item = items[0]
                    cog_href = None
                    for asset in item.get("assets", {}).values():
                        if "data" in asset.get("roles", []):
                            cog_href = asset.get("href")
                            break
                    if cog_href:
                        tile_url = f"{titiler_url()}/cog/tilejson.json?url={cog_href}"
                        return {
                            "type": "raster",
                            "stac_item": item["id"],
                            "tile_url": tile_url,
                        }
        except Exception:
            pass

    if ds["modality"] == "tabular":
        return {"type": "tabular", "hint": "use /datasets/{id}/query with Cube"}

    return {"type": ds["modality"], "hint": "preview not available"}


def terria_link(dataset_id: str) -> str | None:
    ds = get_dataset(dataset_id)
    if ds is None:
        return None
    import json
    import urllib.parse

    share = {"initSources": [{"workbench": [dataset_id]}]}
    encoded = urllib.parse.quote(json.dumps(share, separators=(",", ":")))
    return f"http://localhost:3001/#start={encoded}"
