"""OSM health facilities, an `osm_source` connector backed by the live
Overpass API (OpenStreetMap). Real, community-contributed data — every
run re-queries Overpass rather than replaying a synthetic fixture.

Geometry follows the same V2 bridge pattern as `file_source`: a WKB
`binary` column plus explicit bbox columns, CRS recorded in the Iceberg
table's properties. Overpass always returns WGS84 (EPSG:4326).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import boto3
import pyarrow as pa
from connectors_base.catalog import get_catalog
from connectors_base.checksum import sha256_file
from connectors_base.manifest import Manifest, load_manifest
from connectors_base.pipeline_run import PipelineRunRecorder
from connectors_base.quality import QualityContext, run_checks
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError
from shapely.geometry import Point

from connectors_osm_source.overpass_client import DEFAULT_ENDPOINT, build_query, run_query

CRS = "EPSG:4326"
TAG_KEY = "amenity"
TAG_VALUE = "hospital"

NORMALISED_SCHEMA = pa.schema(
    [
        ("osm_id", pa.string()),
        ("osm_type", pa.string()),
        ("name", pa.string()),
        ("amenity", pa.string()),
        ("geometry", pa.binary()),
        ("bbox_minx", pa.float64()),
        ("bbox_miny", pa.float64()),
        ("bbox_maxx", pa.float64()),
        ("bbox_maxy", pa.float64()),
    ]
)

RAW_BUCKET = "raw"


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


def _table_identifier(manifest: Manifest) -> str:
    namespace, _, name = manifest.target.zone.partition("/")
    return f"{namespace}.{name}"


def _element_point(element: dict) -> tuple[float, float] | None:
    """Nodes carry `lat`/`lon` directly; ways/relations carry a `center`
    (present because the query uses `out center`). Elements with neither
    (rare, e.g. a relation Overpass couldn't resolve) are skipped."""
    if "lat" in element and "lon" in element:
        return element["lon"], element["lat"]
    center = element.get("center")
    if center:
        return center["lon"], center["lat"]
    return None


def _rows_from_elements(elements: list[dict]) -> list[dict]:
    rows = []
    for element in elements:
        point = _element_point(element)
        if point is None:
            continue
        lon, lat = point
        tags = element.get("tags", {})
        rows.append(
            {
                "osm_id": f"{element['type']}/{element['id']}",
                "osm_type": element["type"],
                "name": tags.get("name"),
                "amenity": tags.get(TAG_KEY),
                "geometry": Point(lon, lat).wkb,
                "bbox_minx": lon,
                "bbox_miny": lat,
                "bbox_maxx": lon,
                "bbox_maxy": lat,
            }
        )
    return rows


def run(manifest_path: str | Path) -> PipelineRunRecorder:
    manifest = load_manifest(manifest_path)
    endpoint = manifest.source.endpoint or DEFAULT_ENDPOINT

    with PipelineRunRecorder(manifest) as run_record:
        query = build_query(TAG_KEY, TAG_VALUE)

        # --- extract: live call to the real Overpass API --------------------
        response = run_query(query, endpoint=endpoint)

        # --- output 1: raw artifact with checksum ----------------------------
        with tempfile.TemporaryDirectory() as tmp:
            raw_path_local = Path(tmp) / "raw.json"
            raw_path_local.write_text(json.dumps(response), encoding="utf-8")

            checksum = sha256_file(raw_path_local)
            raw_key = f"{manifest.id}/{run_record.run_id}/raw.json"
            _s3_client().upload_file(str(raw_path_local), RAW_BUCKET, raw_key)
            run_record.record_raw_artifact(f"s3://{RAW_BUCKET}/{raw_key}", checksum)

        # --- normalise: Overpass elements -> V2 bridge geometry table -------
        rows = _rows_from_elements(response.get("elements", []))
        table = pa.Table.from_pylist(rows, schema=NORMALISED_SCHEMA)

        # --- output 2: normalised asset (GeoParquet) -------------------------
        import pyarrow.parquet as pq

        with tempfile.TemporaryDirectory() as tmp:
            normalised_path_local = Path(tmp) / "normalised.geoparquet"
            pq.write_table(table, normalised_path_local)
            normalised_key = f"{manifest.id}/{run_record.run_id}/normalised.geoparquet"
            _s3_client().upload_file(str(normalised_path_local), RAW_BUCKET, normalised_key)
            run_record.record_normalised_asset(f"s3://{RAW_BUCKET}/{normalised_key}", "geoparquet")

        run_record.record_row_count(table.num_rows)

        # --- output 3: catalog registration (CRS in table properties) -------
        table_identifier = _table_identifier(manifest)
        namespace = table_identifier.split(".")[0]
        catalog = get_catalog()
        try:
            catalog.create_namespace(namespace)
        except NamespaceAlreadyExistsError:
            pass
        try:
            iceberg_table = catalog.create_table(
                table_identifier,
                schema=NORMALISED_SCHEMA,
                properties={"geometry.crs": CRS, "geometry.encoding": "wkb+bbox"},
            )
        except TableAlreadyExistsError:
            iceberg_table = catalog.load_table(table_identifier)
        iceberg_table.overwrite(table)
        run_record.record_catalog_registration(table_identifier, iceberg_table.metadata_location)

        # --- output 4: quality report ------------------------------------------
        passed, report = run_checks(
            table,
            table_name=table_identifier.replace(".", "_"),
            checks=manifest.quality.checks,
            ctx=QualityContext(expected_schema=NORMALISED_SCHEMA, crs=CRS),
        )
        run_record.record_quality_report(passed, report)

    return run_record
