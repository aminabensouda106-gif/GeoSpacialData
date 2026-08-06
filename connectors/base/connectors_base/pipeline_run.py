"""The shared PipelineRun record (MASTER_PROMPT §7, M3).

Every pipeline run must produce all five outputs: raw artifact with
checksum, normalised asset, catalog registration, run/lineage record,
quality report. `PipelineRunRecorder` is a context manager that makes this
a framework guarantee rather than a convention: if a connector exits the
`with` block having skipped one of the first three outputs or the quality
report, the recorder raises `IncompletePipelineRunError` itself and still
persists the row to `platform.pipeline_runs` with `status="failed"`, so
the gap shows up in lineage instead of silently vanishing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pyarrow as pa
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError

from connectors_base.catalog import get_catalog
from connectors_base.manifest import Manifest

TABLE_IDENTIFIER = "platform.pipeline_runs"

PIPELINE_RUNS_SCHEMA = pa.schema(
    [
        ("run_id", pa.string()),
        ("dataset_id", pa.string()),
        ("source_type", pa.string()),
        ("status", pa.string()),
        ("started_at", pa.timestamp("us", tz="UTC")),
        ("finished_at", pa.timestamp("us", tz="UTC")),
        ("raw_artifact_path", pa.string()),
        ("raw_artifact_checksum", pa.string()),
        ("normalised_asset_path", pa.string()),
        ("normalised_asset_format", pa.string()),
        ("catalog_table", pa.string()),
        ("catalog_metadata_location", pa.string()),
        ("quality_passed", pa.bool_()),
        ("quality_report", pa.string()),
        ("row_count", pa.int64()),
        ("error", pa.string()),
    ]
)

REQUIRED_OUTPUTS = (
    "raw_artifact",
    "normalised_asset",
    "catalog_registration",
    "quality_report",
)


class IncompletePipelineRunError(Exception):
    """Raised when a pipeline run finishes without all required outputs."""


class PipelineRunRecorder:
    def __init__(self, manifest: Manifest):
        self.manifest = manifest
        self.run_id = str(uuid4())
        self.started_at = datetime.now(timezone.utc)
        self._raw: tuple[str, str] | None = None
        self._normalised: tuple[str, str] | None = None
        self._catalog: tuple[str, str] | None = None
        self._quality: tuple[bool, dict[str, Any]] | None = None
        self._row_count: int | None = None

    def record_raw_artifact(self, path: str, checksum: str) -> None:
        self._raw = (path, checksum)

    def record_normalised_asset(self, path: str, format: str) -> None:
        self._normalised = (path, format)

    def record_catalog_registration(self, table: str, metadata_location: str) -> None:
        self._catalog = (table, metadata_location)

    def record_quality_report(self, passed: bool, report: dict[str, Any]) -> None:
        self._quality = (passed, report)

    def record_row_count(self, row_count: int) -> None:
        self._row_count = row_count

    @property
    def row_count(self) -> int | None:
        return self._row_count

    @property
    def catalog_registration(self) -> tuple[str, str] | None:
        return self._catalog

    @property
    def quality_result(self) -> tuple[bool, dict[str, Any]] | None:
        return self._quality

    def _missing_outputs(self) -> list[str]:
        missing = []
        if self._raw is None:
            missing.append("raw_artifact")
        if self._normalised is None:
            missing.append("normalised_asset")
        if self._catalog is None:
            missing.append("catalog_registration")
        if self._quality is None:
            missing.append("quality_report")
        return missing

    def __enter__(self) -> "PipelineRunRecorder":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        finished_at = datetime.now(timezone.utc)

        if exc_type is not None:
            self._write(finished_at, status="failed", error=f"{exc_type.__name__}: {exc}")
            return False  # propagate the original exception

        missing = self._missing_outputs()
        if missing:
            error = IncompletePipelineRunError(
                f"pipeline run {self.run_id} for dataset {self.manifest.id!r} "
                f"produced fewer than the five required outputs; missing: "
                f"{', '.join(missing)}"
            )
            self._write(finished_at, status="failed", error=str(error))
            raise error

        self._write(finished_at, status="success", error=None)
        return False

    def _write(self, finished_at: datetime, status: str, error: str | None) -> None:
        raw_path, raw_checksum = self._raw or (None, None)
        norm_path, norm_format = self._normalised or (None, None)
        catalog_table, catalog_metadata_location = self._catalog or (None, None)
        quality_passed, quality_report = self._quality or (None, None)

        row = pa.table(
            {
                "run_id": [self.run_id],
                "dataset_id": [self.manifest.id],
                "source_type": [self.manifest.source.type],
                "status": [status],
                "started_at": [self.started_at],
                "finished_at": [finished_at],
                "raw_artifact_path": [raw_path],
                "raw_artifact_checksum": [raw_checksum],
                "normalised_asset_path": [norm_path],
                "normalised_asset_format": [norm_format],
                "catalog_table": [catalog_table],
                "catalog_metadata_location": [catalog_metadata_location],
                "quality_passed": [quality_passed],
                "quality_report": [json.dumps(quality_report) if quality_report is not None else None],
                "row_count": [self._row_count],
                "error": [error],
            },
            schema=PIPELINE_RUNS_SCHEMA,
        )

        catalog = get_catalog()
        try:
            catalog.create_namespace("platform")
        except NamespaceAlreadyExistsError:
            pass

        try:
            table = catalog.create_table(TABLE_IDENTIFIER, schema=PIPELINE_RUNS_SCHEMA)
        except TableAlreadyExistsError:
            table = catalog.load_table(TABLE_IDENTIFIER)
        table.append(row)
