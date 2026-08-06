"""Thin wrapper around the `ogrinfo`/`ogr2ogr` CLIs (GDAL/OGR) — MASTER_PROMPT
M3 asks for "GDAL/OGR -> GeoParquet -> Iceberg" for boundary datasets, and
specifically to hard-fail if the source's CRS is undeclared. We shell out
to the CLI tools rather than the `osgeo` Python bindings: `gdal-bin`
(apt) ships a different system Python than the `python:3.12-slim` base
image's interpreter, so the bindings wouldn't be importable from our
venv without a fragile cross-interpreter apt/pip mix.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class CRSNotDeclaredError(Exception):
    """The source file has no declared coordinate reference system."""


def detect_crs(source_path: Path) -> str:
    """Return the source layer's CRS as a WKT string. Raises
    `CRSNotDeclaredError` if GDAL reports no coordinate system at all —
    this is the hard-fail the master prompt requires for Dataset B."""
    result = subprocess.run(
        ["ogrinfo", "-json", "-so", str(source_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CRSNotDeclaredError(
            f"ogrinfo failed to read {source_path}: {result.stderr.strip()}"
        )

    info = json.loads(result.stdout)
    layers = info.get("layers") or []
    if not layers:
        raise CRSNotDeclaredError(f"{source_path}: ogrinfo reported no layers")

    geometry_fields = layers[0].get("geometryFields") or []
    if not geometry_fields:
        raise CRSNotDeclaredError(f"{source_path}: ogrinfo reported no geometry field")

    coordinate_system = geometry_fields[0].get("coordinateSystem")
    wkt = (coordinate_system or {}).get("wkt")
    if not wkt:
        raise CRSNotDeclaredError(
            f"{source_path}: no coordinate reference system declared on the source "
            "layer — refusing to ingest an undeclared-CRS boundary dataset "
            "(MASTER_PROMPT M3 hard-fail rule)"
        )
    return wkt


def convert_to_geojson(source_path: Path, dest_path: Path) -> None:
    """Run `ogr2ogr` to normalise the source vector file to GeoJSON, which
    we then parse in Python (via shapely) to build the V2 bridge
    GeoParquet table (WKB + explicit bbox columns)."""
    result = subprocess.run(
        ["ogr2ogr", "-f", "GeoJSON", str(dest_path), str(source_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ogr2ogr failed converting {source_path}: {result.stderr.strip()}")
