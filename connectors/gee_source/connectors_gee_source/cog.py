"""Write a composite array as a Cloud-Optimized GeoTIFF and upload it to
SeaweedFS — MASTER_PROMPT M4's "Path B" (direct pull via `xee`/
`computePixels`, no GCS staging bucket): in the fixture-mode POC that
means straight from the in-process numpy array to the object store, with
no intermediate bucket at all.
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds

SERVING_BUCKET = "serving"


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333"),
        aws_access_key_id=os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
        aws_secret_access_key=os.environ.get(
            "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
        ),
        region_name="local-01",
    )


def write_cog(
    array: np.ndarray,
    bbox: tuple[float, float, float, float],
    crs: str,
    output_path: Path,
) -> None:
    height, width = array.shape
    transform = from_bounds(*bbox, width, height)
    block_size = min(256, width, height)
    # TIFF tile dimensions must be multiples of 16.
    block_size = max(16, (block_size // 16) * 16)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": height,
        "width": width,
        "crs": crs,
        "transform": transform,
        "tiled": True,
        "blockxsize": block_size,
        "blockysize": block_size,
        "compress": "deflate",
    }
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(array, 1)
        if min(height, width) >= 8:
            dst.build_overviews([2, 4], Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")


def upload_cog(local_path: Path, dataset_id: str, period: str) -> str:
    key = f"cog/{dataset_id}/{period}.tif"
    get_s3_client().upload_file(str(local_path), SERVING_BUCKET, key)
    return f"http://seaweedfs:8333/{SERVING_BUCKET}/{key}"
