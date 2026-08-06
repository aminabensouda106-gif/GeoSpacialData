"""Read helpers over `platform.pipeline_runs`, used by Dagster asset
checks to surface the quality outcome a connector run already recorded
via `PipelineRunRecorder.record_quality_report` — rather than re-running
Soda Core a second time just for the Dagster UI."""

from __future__ import annotations

import json
from typing import Any

import pyarrow.compute as pc
from pyiceberg.exceptions import NoSuchTableError

from connectors_base.catalog import get_catalog
from connectors_base.pipeline_run import TABLE_IDENTIFIER


def latest_quality_result(dataset_id: str) -> tuple[bool, dict[str, Any]] | None:
    """Return (passed, report) for the most recent run of `dataset_id`
    that recorded a quality report, or None if there isn't one yet."""
    catalog = get_catalog()
    try:
        table = catalog.load_table(TABLE_IDENTIFIER)
    except NoSuchTableError:
        return None

    arrow_table = table.scan().to_arrow()
    filtered = arrow_table.filter(pc.equal(arrow_table["dataset_id"], dataset_id))
    if filtered.num_rows == 0:
        return None

    order = pc.sort_indices(filtered, sort_keys=[("finished_at", "descending")])
    latest = filtered.take(order[:1]).to_pylist()[0]

    if latest["quality_passed"] is None:
        return None

    report = json.loads(latest["quality_report"]) if latest["quality_report"] else {}
    return bool(latest["quality_passed"]), report
