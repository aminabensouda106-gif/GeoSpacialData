"""V2-bridge Iceberg table -> GeoJSON -> tippecanoe -> PMTiles (MASTER_PROMPT
M3 publish step). Reads back the WKB + bbox columns written by
`pipeline.run`, reconstitutes GeoJSON features, and shells out to
`tippecanoe` (built from source into the Dagster image) to produce a
PMTiles archive uploaded to `s3://serving/pmtiles/`.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import boto3
from shapely import wkb
from shapely.geometry import mapping

from connectors_base.catalog import get_catalog

SERVING_BUCKET = "serving"


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333"),
        aws_access_key_id=os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
        aws_secret_access_key=os.environ.get(
            "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
        ),
        region_name="local-01",
    )


def iceberg_table_to_geojson(table_identifier: str, id_property: str) -> dict:
    """Scan an Iceberg table written with the V2 bridge geometry pattern
    (WKB `geometry` column + bbox columns) and return a GeoJSON
    FeatureCollection dict."""
    catalog = get_catalog()
    table = catalog.load_table(table_identifier)
    arrow_table = table.scan().to_arrow()
    rows = arrow_table.to_pylist()

    features = []
    for row in rows:
        geometry = wkb.loads(row.pop("geometry"))
        row.pop("bbox_minx", None)
        row.pop("bbox_miny", None)
        row.pop("bbox_maxx", None)
        row.pop("bbox_maxy", None)
        features.append(
            {
                "type": "Feature",
                "properties": row,
                "id": row[id_property],
                "geometry": mapping(geometry),
            }
        )
    return {"type": "FeatureCollection", "features": features}


MIN_ZOOM = 0
MAX_ZOOM = 14


def build_pmtiles(geojson: dict, layer_name: str, output_path: Path) -> None:
    """Zoom range is fixed (rather than `-zg` auto-detection) so the
    published-layers registry can record an exact min/max zoom without
    parsing tippecanoe's stderr for the value it picked."""
    geojson_path = output_path.with_suffix(".geojson")
    with geojson_path.open("w", encoding="utf-8") as fh:
        json.dump(geojson, fh)

    result = subprocess.run(
        [
            "tippecanoe",
            "-o", str(output_path),
            "-l", layer_name,
            "-Z", str(MIN_ZOOM),
            "-z", str(MAX_ZOOM),
            "--force",
            str(geojson_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tippecanoe failed for {layer_name}: {result.stderr.strip()}")


def upload_pmtiles(local_path: Path, dataset_id: str) -> str:
    key = f"pmtiles/{dataset_id}.pmtiles"
    _s3_client().upload_file(str(local_path), SERVING_BUCKET, key)
    return f"s3://{SERVING_BUCKET}/{key}"


def geojson_bbox(geojson: dict) -> tuple[float, float, float, float]:
    from shapely.geometry import shape

    geoms = [shape(f["geometry"]) for f in geojson["features"]]
    minx = min(g.bounds[0] for g in geoms)
    miny = min(g.bounds[1] for g in geoms)
    maxx = max(g.bounds[2] for g in geoms)
    maxy = max(g.bounds[3] for g in geoms)
    return (minx, miny, maxx, maxy)
