"""ors_isochrones_15min (ors_source, live OpenRouteService API pull —
real data, no synthetic fixture). Requires ORS_API_KEY in the
environment; see connectors_ors_source.ors_client."""

from connectors_base.repo_paths import repo_root
from connectors_ors_source.pipeline import run as run_ors_isochrones_15min
from dagster import AssetExecutionContext, MaterializeResult, asset


@asset(key_prefix="bronze", name="ors_isochrones_15min")
def ors_isochrones_15min(context: AssetExecutionContext) -> MaterializeResult:
    manifest_path = repo_root() / "recipes" / "datasets" / "ors_isochrones_15min.yaml"
    run_record = run_ors_isochrones_15min(manifest_path)

    context.log.info(
        f"Pipeline run {run_record.run_id} for {run_record.manifest.id} finished; "
        f"row_count={run_record.row_count}"
    )

    catalog_registration = run_record.catalog_registration
    quality_result = run_record.quality_result

    return MaterializeResult(
        metadata={
            "run_id": run_record.run_id,
            "row_count": run_record.row_count,
            "catalog_table": catalog_registration[0] if catalog_registration else None,
            "quality_passed": quality_result[0] if quality_result else None,
        }
    )
