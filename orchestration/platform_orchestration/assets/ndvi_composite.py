"""M4 Dataset C: ndvi_composite (gee_source, fixture mode). Each
materialization runs the full period catalog but only reprocesses periods
whose contributing-asset hash changed since the last run (see
connectors_gee_source.pipeline for the set-difference change detection
this relies on)."""

from connectors_base.repo_paths import repo_root
from connectors_gee_source.pipeline import run as run_ndvi_composite
from dagster import AssetExecutionContext, MaterializeResult, asset


@asset(key_prefix="serving", name="ndvi_composite")
def ndvi_composite(context: AssetExecutionContext) -> MaterializeResult:
    recipe_path = repo_root() / "recipes" / "gee" / "ndvi_composite.yaml"
    reprocessed = run_ndvi_composite(recipe_path)

    period_ids = [record.manifest.id for record in reprocessed]
    context.log.info(f"Reprocessed {len(reprocessed)} period(s): {period_ids}")

    return MaterializeResult(
        metadata={
            "reprocessed_periods": period_ids,
            "reprocessed_count": len(reprocessed),
        }
    )
