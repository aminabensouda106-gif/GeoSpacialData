"""Dataset B: `communes_boundaries`, a `file_source` connector.

GDAL/OGR -> GeoParquet -> Iceberg, per MASTER_PROMPT M3. Geometry uses
the V2 bridge pattern rather than Iceberg v3 native geo types: a WKB
`binary` column, explicit `bbox_minx/miny/maxx/maxy` columns, and the
source CRS recorded in the Iceberg table's properties. An undeclared CRS
on the source file is a hard failure, not a warning.
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
from connectors_base.repo_paths import repo_root
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError
from shapely.geometry import shape

from connectors_file_source.gdal_ogr import convert_to_geojson, detect_crs

NORMALISED_SCHEMA = pa.schema(
    [
        ("commune_code", pa.string()),
        ("commune_name", pa.string()),
        ("region_name", pa.string()),
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


def run(manifest_path: str | Path) -> PipelineRunRecorder:
    manifest = load_manifest(manifest_path)

    with PipelineRunRecorder(manifest) as run_record:
        source_path = repo_root() / manifest.source.endpoint

        # --- output 1: raw artifact with checksum ---------------------------
        checksum = sha256_file(source_path)
        raw_key = f"{manifest.id}/{run_record.run_id}/{source_path.name}"
        _s3_client().upload_file(str(source_path), RAW_BUCKET, raw_key)
        run_record.record_raw_artifact(f"s3://{RAW_BUCKET}/{raw_key}", checksum)

        # Hard-fail if the source has no declared CRS. This raises before
        # any further output is recorded, so the run is left incomplete
        # and PipelineRunRecorder.__exit__ persists it as status=failed.
        crs = detect_crs(source_path)

        # --- GDAL/OGR: normalise to GeoJSON, then build the V2 bridge table --
        with tempfile.TemporaryDirectory() as tmp:
            converted_path = Path(tmp) / "converted.geojson"
            convert_to_geojson(source_path, converted_path)
            geojson = json.loads(converted_path.read_text(encoding="utf-8"))

        rows = []
        for feature in geojson["features"]:
            geom = shape(feature["geometry"])
            minx, miny, maxx, maxy = geom.bounds
            props = feature["properties"]
            rows.append(
                {
                    "commune_code": props["commune_code"],
                    "commune_name": props["commune_name"],
                    "region_name": props["region_name"],
                    "geometry": geom.wkb,
                    "bbox_minx": minx,
                    "bbox_miny": miny,
                    "bbox_maxx": maxx,
                    "bbox_maxy": maxy,
                }
            )
        table = pa.Table.from_pylist(rows, schema=NORMALISED_SCHEMA)

        # --- output 2: normalised asset (GeoParquet, V2 bridge geometry) ----
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
                properties={"geometry.crs": crs, "geometry.encoding": "wkb+bbox"},
            )
        except TableAlreadyExistsError:
            iceberg_table = catalog.load_table(table_identifier)
        iceberg_table.overwrite(table)
        run_record.record_catalog_registration(table_identifier, iceberg_table.metadata_location)

        # --- output 4: quality report ----------------------------------------
        passed, report = run_checks(
            table,
            table_name=table_identifier.replace(".", "_"),
            checks=manifest.quality.checks,
            ctx=QualityContext(expected_schema=NORMALISED_SCHEMA, crs=crs),
        )
        run_record.record_quality_report(passed, report)

    return run_record
