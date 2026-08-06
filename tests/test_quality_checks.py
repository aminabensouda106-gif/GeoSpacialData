"""Unit tests for connectors_base.quality — no Docker services required,
Soda Core runs against an in-memory DuckDB view."""

import pyarrow as pa
from connectors_base.quality import QualityContext, run_checks

SCHEMA = pa.schema(
    [
        ("commune_code", pa.string()),
        ("employment_rate", pa.float64()),
    ]
)


def _table(rows):
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def test_checks_pass_on_good_data():
    table = _table(
        [
            {"commune_code": "01-001", "employment_rate": 8.5},
            {"commune_code": "01-002", "employment_rate": 12.0},
        ]
    )
    passed, report = run_checks(
        table,
        table_name="good_table",
        checks=["schema_conformance", "no_nulls:commune_code", "value_range"],
        ctx=QualityContext(
            expected_schema=SCHEMA, value_ranges={"employment_rate": (0.0, 100.0)}
        ),
    )
    assert passed is True
    assert report["passed"] is True


def test_checks_fail_on_null_required_column():
    table = _table(
        [
            {"commune_code": "01-001", "employment_rate": 8.5},
            {"commune_code": None, "employment_rate": 12.0},
        ]
    )
    passed, report = run_checks(
        table,
        table_name="null_table",
        checks=["no_nulls:commune_code"],
    )
    assert passed is False
    assert "missing_count" in report["failed_checks"]


def test_checks_fail_on_out_of_range_value():
    table = _table(
        [
            {"commune_code": "01-001", "employment_rate": 8.5},
            {"commune_code": "01-002", "employment_rate": 250.0},
        ]
    )
    passed, report = run_checks(
        table,
        table_name="range_table",
        checks=["value_range"],
        ctx=QualityContext(value_ranges={"employment_rate": (0.0, 100.0)}),
    )
    assert passed is False


def test_checks_fail_on_missing_column():
    table = _table([{"commune_code": "01-001", "employment_rate": 8.5}])
    passed, report = run_checks(
        table,
        table_name="schema_table",
        checks=["schema_conformance"],
        ctx=QualityContext(
            expected_schema=pa.schema(
                [("commune_code", pa.string()), ("period", pa.date32())]
            )
        ),
    )
    assert passed is False
