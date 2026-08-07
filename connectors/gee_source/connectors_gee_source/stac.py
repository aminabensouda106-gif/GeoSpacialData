"""Publish STAC collections/items to `stac-api` (transactions extension).
Items carry the `processing:` extension fields plus the contributing-asset
manifest, and always surface `gee:provenance_mode` — MASTER_PROMPT M4:
"Without EE credentials, run against sample-data/gee_fixtures/, set
provenance.mode = 'fixture', and surface that in both front ends." This
is the surfacing point on the catalog side.
"""

from __future__ import annotations

import os
from datetime import datetime

import pystac
import requests

STAC_API_URL_DEFAULT = "http://stac-api:8080"


def stac_api_url() -> str:
    return os.environ.get("STAC_API_URL", STAC_API_URL_DEFAULT)


def ensure_collection(
    collection_id: str,
    title: str,
    description: str,
    license: str,
    bbox: tuple[float, float, float, float],
    temporal_start: datetime,
) -> None:
    url = f"{stac_api_url()}/collections/{collection_id}"
    if requests.get(url, timeout=10).status_code == 200:
        return

    collection = pystac.Collection(
        id=collection_id,
        title=title,
        description=description,
        license=license,
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([list(bbox)]),
            temporal=pystac.TemporalExtent([[temporal_start, None]]),
        ),
    )
    resp = requests.post(f"{stac_api_url()}/collections", json=collection.to_dict(), timeout=10)
    resp.raise_for_status()


def publish_item(
    *,
    collection_id: str,
    item_id: str,
    bbox: tuple[float, float, float, float],
    geometry: dict,
    period_start: datetime,
    period_end: datetime,
    cog_href: str,
    recipe_id: str,
    contributing_assets: list[str],
    contributing_assets_hash: str,
    provenance_sentence: str,
) -> dict:
    item = pystac.Item(
        id=item_id,
        geometry=geometry,
        bbox=list(bbox),
        datetime=period_start,
        properties={
            "start_datetime": period_start.isoformat(),
            "end_datetime": period_end.isoformat(),
            "processing:facility": "GeoSpacialData POC",
            "processing:software": {"connectors_gee_source": "0.1.0"},
            "processing:lineage": provenance_sentence,
            "gee:recipe_id": recipe_id,
            "gee:provenance_mode": "fixture",
            "gee:contributing_assets": sorted(contributing_assets),
            "gee:contributing_assets_hash": contributing_assets_hash,
        },
        collection=collection_id,
    )
    item.add_asset(
        "data",
        pystac.Asset(
            href=cog_href,
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["data"],
            title=f"{item_id} COG",
        ),
    )
    item_dict = item.to_dict()

    base = f"{stac_api_url()}/collections/{collection_id}/items"
    exists = requests.get(f"{base}/{item_id}", timeout=10).status_code == 200
    if exists:
        resp = requests.put(f"{base}/{item_id}", json=item_dict, timeout=10)
    else:
        resp = requests.post(base, json=item_dict, timeout=10)
    resp.raise_for_status()
    return item_dict
