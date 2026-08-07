"""Soda Core quality checks, run against an in-memory DuckDB view of a
connector's output table.

Manifests declare checks as short mnemonics (MASTER_PROMPT §8.1):
`schema_conformance`, `no_nulls:<cols>`, `crs_declared`, `value_range`.
This module expands each into concrete SodaCL and returns a
JSON-serialisable report plus a pass/fail bool — both are fed into
`PipelineRunRecorder.record_quality_report`, which is one of the five
outputs the framework requires from every run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import duckdb
import pyarrow as pa
from soda.scan import Scan


@dataclass
class QualityContext:
    """Dataset-specific inputs the shorthand checks need to expand into
    concrete SodaCL: `schema_conformance` needs the expected column list,
    `value_range` needs per-column bounds, `crs_declared` needs the CRS
    that was actually recorded on the table."""

    expected_schema: pa.Schema | None = None
    value_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    crs: str | None = None


class UnknownQualityCheckError(Exception):
    pass


def _expand(check: str, ctx: QualityContext) -> list[str]:
    if check == "schema_conformance":
        if ctx.expected_schema is None:
            raise ValueError("schema_conformance check requires ctx.expected_schema")
        # "fail: when required column missing: [a, b]" on one line is ambiguous
        # plain YAML (two colons) and gets rejected before SodaCL ever sees it;
        # "when required column missing" must be its own nested key under fail.
        columns = ", ".join(f.name for f in ctx.expected_schema)
        return [
            "  - schema:",
            "      fail:",
            f"        when required column missing: [{columns}]",
        ]

    if check.startswith("no_nulls:"):
        cols = check.split(":", 1)[1].split(",")
        return [f"  - missing_count({col.strip()}) = 0" for col in cols]

    if check == "value_range":
        lines = []
        for col, (lo, hi) in ctx.value_ranges.items():
            lines.append(f"  - min({col}) >= {lo}")
            lines.append(f"  - max({col}) <= {hi}")
        return lines

    if check == "crs_declared":
        # The hard structural enforcement happens at load time in
        # file_source (undeclared CRS aborts the run before it gets this
        # far) — this line just makes the check visible in the report.
        if not ctx.crs:
            raise ValueError("crs_declared check failed: no CRS recorded on the table")
        return [f"# crs_declared: {ctx.crs} (enforced at load time)"]

    raise UnknownQualityCheckError(f"unknown quality check: {check!r}")


def run_checks(
    table: pa.Table,
    table_name: str,
    checks: list[str],
    ctx: QualityContext | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Run `checks` (as declared in a manifest's `quality.checks`) against
    `table` via an in-memory DuckDB-backed Soda Core scan. Returns
    (passed, report) where `report` is JSON-serialisable."""
    ctx = ctx or QualityContext()

    con = duckdb.connect()
    con.register(table_name, table)

    sodacl_lines = [f"checks for {table_name}:", "  - row_count > 0"]
    for check in checks:
        sodacl_lines.extend(_expand(check, ctx))
    sodacl = "\n".join(sodacl_lines)

    scan = Scan()
    scan.set_scan_definition_name(f"{table_name}_quality")
    scan.add_duckdb_connection(con, data_source_name=table_name)
    scan.set_data_source_name(table_name)
    scan.add_sodacl_yaml_str(sodacl)
    scan.execute()

    passed = not scan.has_check_fails()
    report = {
        "sodacl": sodacl,
        "passed": passed,
        "failed_checks": scan.get_checks_fail_text() or "",
        "logs": scan.get_logs_text() or "",
    }
    return passed, report
