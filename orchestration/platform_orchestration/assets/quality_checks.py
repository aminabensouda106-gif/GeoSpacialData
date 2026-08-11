"""M3: Soda Core checks surfaced as Dagster asset checks.

Each connector run already executes its manifest's `quality.checks` via
`connectors_base.quality.run_checks` and records the outcome on its
`PipelineRun` row (MASTER_PROMPT M3 — quality report is one of the five
required outputs). These asset checks read that recorded outcome back so
it shows up natively in the Dagster UI against the asset it belongs to,
without re-running the scan.
"""

from connectors_base.pipeline_runs_query import latest_quality_result
from dagster import AssetCheckResult, MetadataValue, asset_check

from platform_orchestration.assets.communes_boundaries import communes_boundaries


@asset_check(asset=communes_boundaries, name="soda_quality")
def communes_boundaries_quality() -> AssetCheckResult:
    result = latest_quality_result("communes_boundaries")
    if result is None:
        return AssetCheckResult(passed=False, description="No pipeline run has recorded a quality report yet")
    passed, report = result
    return AssetCheckResult(
        passed=passed,
        metadata={"report": MetadataValue.json(report)},
    )
