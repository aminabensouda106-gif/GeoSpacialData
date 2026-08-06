"""Dataset A: `employment_indicators`, an `api_source` connector built on
dlt. Extraction pulls from the synthetic generator in
`sample-data/employment_indicators_generator.py` rather than a real
statistics-office API, so the pipeline runs end to end with zero
credentials (MASTER_PROMPT M3).

Produces all five outputs the framework requires for every run: raw
JSONL with checksum, a normalised Parquet file, an Iceberg table
registration, the `PipelineRun` lineage record (written by
`PipelineRunRecorder` itself), and a Soda Core quality report.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from datetime import date
from pathlib import Path

import boto3
import dlt
import pyarrow as pa
import pyarrow.parquet as pq
from connectors_base.catalog import get_catalog
from connectors_base.checksum import sha256_file
from connectors_base.manifest import Manifest, load_manifest
from connectors_base.pipeline_run import PipelineRunRecorder
from connectors_base.quality import QualityContext, run_checks
from connectors_base.repo_paths import repo_root
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError

NORMALISED_SCHEMA = pa.schema(
    [
        ("commune_code", pa.string()),
        ("commune_name", pa.string()),
        ("period", pa.date32()),
        ("employment_count", pa.int64()),
        ("employment_rate", pa.float64()),
    ]
)

RAW_BUCKET = "raw"


def _load_generator():
    """Import the generator by file path rather than as an installed
    package — `sample-data/` holds fixtures and small scripts shared
    across connectors, not a Python distribution."""
    generator_path = repo_root() / "sample-data" / "employment_indicators_generator.py"
    spec = importlib.util.spec_from_file_location(
        "employment_indicators_generator", generator_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.generate_records


@dlt.resource(name="employment_indicators")
def employment_indicators_resource():
    generate_records = _load_generator()
    yield from generate_records()


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
        records = list(employment_indicators_resource())

        # --- output 1: raw artifact with checksum ---------------------------
        with tempfile.TemporaryDirectory() as tmp:
            raw_path_local = Path(tmp) / "raw.jsonl"
            with open(raw_path_local, "w", encoding="utf-8") as fh:
                for rec in records:
                    fh.write(json.dumps(rec) + "\n")

            checksum = sha256_file(raw_path_local)
            raw_key = f"{manifest.id}/{run_record.run_id}/raw.jsonl"
            _s3_client().upload_file(str(raw_path_local), RAW_BUCKET, raw_key)
            run_record.record_raw_artifact(f"s3://{RAW_BUCKET}/{raw_key}", checksum)

        # --- output 2: normalised asset --------------------------------------
        table = pa.Table.from_pylist(
            [{**rec, "period": date.fromisoformat(rec["period"])} for rec in records],
            schema=NORMALISED_SCHEMA,
        )

        with tempfile.TemporaryDirectory() as tmp:
            normalised_path_local = Path(tmp) / "normalised.parquet"
            pq.write_table(table, normalised_path_local)
            normalised_key = f"{manifest.id}/{run_record.run_id}/normalised.parquet"
            _s3_client().upload_file(str(normalised_path_local), RAW_BUCKET, normalised_key)
            run_record.record_normalised_asset(f"s3://{RAW_BUCKET}/{normalised_key}", "parquet")

        run_record.record_row_count(table.num_rows)

        # --- output 3: catalog registration ----------------------------------
        table_identifier = _table_identifier(manifest)
        namespace = table_identifier.split(".")[0]
        catalog = get_catalog()
        try:
            catalog.create_namespace(namespace)
        except NamespaceAlreadyExistsError:
            pass
        try:
            iceberg_table = catalog.create_table(table_identifier, schema=NORMALISED_SCHEMA)
        except TableAlreadyExistsError:
            iceberg_table = catalog.load_table(table_identifier)
        iceberg_table.overwrite(table)
        run_record.record_catalog_registration(table_identifier, iceberg_table.metadata_location)

        # --- output 4: quality report (output 5, the lineage record itself,
        # is written by PipelineRunRecorder on context exit) -----------------
        passed, report = run_checks(
            table,
            table_name=table_identifier.replace(".", "_"),
            checks=manifest.quality.checks,
            ctx=QualityContext(
                expected_schema=NORMALISED_SCHEMA,
                value_ranges={"employment_rate": (0.0, 100.0)},
            ),
        )
        run_record.record_quality_report(passed, report)

    return run_record
