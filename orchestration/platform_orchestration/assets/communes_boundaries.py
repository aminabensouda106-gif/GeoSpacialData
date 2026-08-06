"""M3 Dataset B: communes_boundaries (file_source, GDAL/OGR-backed)."""

from connectors_base.repo_paths import repo_root
from connectors_file_source.pipeline import run as run_communes_boundaries
from dagster import AssetExecutionContext, MaterializeResult, asset


@asset(key_prefix="bronze", name="communes_boundaries")
def communes_boundaries(context: AssetExecutionContext) -> MaterializeResult:
    manifest_path = repo_root() / "recipes" / "datasets" / "communes_boundaries.yaml"
    run_record = run_communes_boundaries(manifest_path)

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
