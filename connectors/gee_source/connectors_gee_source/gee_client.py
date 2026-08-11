"""Real Google Earth Engine client.

Authenticates via service account key (env var GEE_SERVICE_ACCOUNT_KEY
pointing to the JSON key file). When credentials are absent, the connector
falls back to fixture mode — this module is never imported in that case.
"""

import json
import os
from pathlib import Path

import ee
import numpy as np
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

_initialized = False


def _init():
    global _initialized
    if _initialized:
        return

    key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY", "")
    project = os.environ.get("EE_PROJECT_ID", "")

    if key_path and Path(key_path).is_file() and Path(key_path).stat().st_size > 0:
        key_data = json.loads(Path(key_path).read_text())
        credentials = ee.ServiceAccountCredentials(
            key_data["client_email"], key_file=key_path
        )
        ee.Initialize(credentials)
    elif project:
        ee.Initialize(project=project)
    else:
        raise RuntimeError(
            "No GEE credentials found. Set GEE_SERVICE_ACCOUNT_KEY to a "
            "service-account JSON key, or EE_PROJECT_ID to a GEE project "
            "after running `earthengine authenticate`."
        )
    _initialized = True


def is_available() -> bool:
    key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY", "")
    if key_path:
        p = Path(key_path)
        if p.is_file() and p.stat().st_size > 0:
            return True
    return bool(os.environ.get("EE_PROJECT_ID", ""))


def fetch_sentinel2_scenes(
    aoi_geojson: dict,
    start_date: str,
    end_date: str,
    max_cloud_pct: int = 20,
) -> ee.ImageCollection:
    _init()
    aoi = ee.Geometry(aoi_geojson)
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_pct))
    )


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    scl = image.select("SCL")
    mask = (
        scl.neq(3)   # cloud shadows
        .And(scl.neq(8))   # cloud medium probability
        .And(scl.neq(9))   # cloud high probability
        .And(scl.neq(10))  # thin cirrus
    )
    return image.updateMask(mask)


def compute_ndvi(image: ee.Image, nir: str = "B8", red: str = "B4") -> ee.Image:
    return image.normalizedDifference([nir, red]).rename("NDVI")


def compute_composite(
    aoi_geojson: dict,
    start_date: str,
    end_date: str,
    reducer_type: str = "percentile",
    percentile: int = 90,
    scale_m: int = 500,
    max_cloud_pct: int = 20,
) -> tuple[np.ndarray, list[float], int]:
    """Compute an NDVI composite over the AOI for one period.

    Returns (array, bbox_as_list, scene_count).
    """
    _init()
    aoi = ee.Geometry(aoi_geojson)
    collection = fetch_sentinel2_scenes(
        aoi_geojson, start_date, end_date, max_cloud_pct
    )
    scene_count = collection.size().getInfo()
    if scene_count == 0:
        raise RuntimeError(
            f"No Sentinel-2 scenes found for {start_date} to {end_date} "
            f"with cloud cover < {max_cloud_pct}%"
        )

    masked = collection.map(mask_s2_clouds)
    ndvi_collection = masked.map(lambda img: compute_ndvi(img))

    if reducer_type == "percentile":
        composite = ndvi_collection.reduce(
            ee.Reducer.percentile([percentile])
        ).rename(["NDVI"])
    elif reducer_type == "mean":
        composite = ndvi_collection.mean().rename(["NDVI"])
    elif reducer_type == "max":
        composite = ndvi_collection.max().rename(["NDVI"])
    else:
        raise ValueError(f"Unknown reducer: {reducer_type}")

    composite = composite.clip(aoi)

    pixels = composite.sampleRectangle(
        region=aoi,
        defaultValue=0,
    ).getInfo()

    ndvi_band = pixels["properties"]["NDVI"]
    array = np.array(ndvi_band, dtype=np.float32)

    bounds = aoi.bounds().getInfo()["coordinates"][0]
    west = min(c[0] for c in bounds)
    south = min(c[1] for c in bounds)
    east = max(c[0] for c in bounds)
    north = max(c[1] for c in bounds)

    return array, [west, south, east, north], scene_count


def list_scene_ids(
    aoi_geojson: dict,
    start_date: str,
    end_date: str,
    max_cloud_pct: int = 20,
) -> list[str]:
    _init()
    collection = fetch_sentinel2_scenes(
        aoi_geojson, start_date, end_date, max_cloud_pct
    )
    ids = collection.aggregate_array("system:index").getInfo()
    return ids
