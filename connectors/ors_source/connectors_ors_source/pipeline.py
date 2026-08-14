"""ORS 15-minute driving isochrones, an `ors_source` connector backed by
the live OpenRouteService API. Origins are real commune names (the same
eleven used by `communes_boundaries`) geocoded live via Nominatim, not
synthetic coordinates — only the boundary *shapes* in that older dataset
are synthetic rectangles; the city names and, here, their geocoded
centers are real.

Requires `ORS_API_KEY` in the environment (see `ors_client.py`).
Geometry follows the same V2 bridge pattern as `file_source`/
`osm_source`: a WKB `binary` column plus explicit bbox columns, CRS
recorded in the Iceberg table's properties (ORS returns WGS84).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import boto3
import pyarrow as pa
from connectors_base.catalog import get_catalog
from connectors_base.checksum import sha256_file
from connectors_base.manifest import Manifest, load_manifest
from connectors_base.pipeline_run import PipelineRunRecorder
from connectors_base.quality import QualityContext, run_checks
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError
from shapely.geometry import shape

from connectors_ors_source.geocode import geocode
from connectors_ors_source.ors_client import isochrone

CRS = "EPSG:4326"
RANGE_SECONDS = 900  # 15 minutes

# The same eleven real commune names used by `communes_boundaries`
# (recipes/datasets/communes_boundaries.yaml / sample-data). Geocoded
# live below rather than reused from that dataset's (synthetic) polygon
# centroids, so every coordinate here traces back to a real geocoder.
COMMUNE_NAMES = [
    "Rabat, Morocco",
    "Salé, Morocco",
    "Témara, Morocco",
    "Casablanca, Morocco",
    "Mohammedia, Morocco",
    "Fès, Morocco",
    "Meknès, Morocco",
    "Marrakech, Morocco",
    "Tanger, Morocco",
    "Agadir, Morocco",
    "Laâyoune, Morocco",
]

NORMALISED_SCHEMA = pa.schema(
    [
        ("commune_name", pa.string()),
        ("range_minutes", pa.int64()),
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


def _fetch_isochrones() -> list[dict]:
    """Geocode each commune name (Nominatim) then fetch its 15-minute
    driving isochrone (ORS). Returns the raw ORS responses, one per
    commune that geocoded successfully."""
    responses = []
    for name in COMMUNE_NAMES:
        point = geocode(name)
        time.sleep(1)  # Nominatim usage policy: max ~1 request/second
        if point is None:
            continue
        lon, lat = point
        response = isochrone(lon, lat, RANGE_SECONDS)
        responses.append({"commune_name": name.split(",")[0], "response": response})
    return responses


def _rows_from_responses(responses: list[dict]) -> list[dict]:
    rows = []
    for entry in responses:
        for feature in entry["response"].get("features", []):
            geom = shape(feature["geometry"])
            minx, miny, maxx, maxy = geom.bounds
            rows.append(
                {
                    "commune_name": entry["commune_name"],
                    "range_minutes": RANGE_SECONDS // 60,
                    "geometry": geom.wkb,
                    "bbox_minx": minx,
                    "bbox_miny": miny,
                    "bbox_maxx": maxx,
                    "bbox_maxy": maxy,
                }
            )
    return rows


def run(manifest_path: str | Path) -> PipelineRunRecorder:
    manifest = load_manifest(manifest_path)

    with PipelineRunRecorder(manifest) as run_record:
        # --- extract: live calls to Nominatim (geocode) + ORS (isochrone) ---
        responses = _fetch_isochrones()

        # --- output 1: raw artifact with checksum ----------------------------
        with tempfile.TemporaryDirectory() as tmp:
            raw_path_local = Path(tmp) / "raw.json"
            raw_path_local.write_text(json.dumps(responses), encoding="utf-8")

            checksum = sha256_file(raw_path_local)
            raw_key = f"{manifest.id}/{run_record.run_id}/raw.json"
            _s3_client().upload_file(str(raw_path_local), RAW_BUCKET, raw_key)
            run_record.record_raw_artifact(f"s3://{RAW_BUCKET}/{raw_key}", checksum)

        # --- normalise: ORS GeoJSON features -> V2 bridge geometry table ----
        rows = _rows_from_responses(responses)
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
