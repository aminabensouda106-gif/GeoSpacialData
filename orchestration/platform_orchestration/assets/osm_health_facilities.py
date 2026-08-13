"""osm_health_facilities (osm_source, live Overpass API pull — real data,
no synthetic fixture)."""

from connectors_base.repo_paths import repo_root
from connectors_osm_source.pipeline import run as run_osm_health_facilities
from dagster import AssetExecutionContext, MaterializeResult, asset


@asset(key_prefix="bronze", name="osm_health_facilities")
def osm_health_facilities(context: AssetExecutionContext) -> MaterializeResult:
    manifest_path = repo_root() / "recipes" / "datasets" / "osm_health_facilities.yaml"
    run_record = run_osm_health_facilities(manifest_path)

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
