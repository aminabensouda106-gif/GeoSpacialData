"""M3 publish step: bronze.communes_boundaries -> tippecanoe -> PMTiles on
s3://serving/, registered in platform.published_layers for the M7 Terria
catalog generator to read."""

import tempfile
from pathlib import Path

from connectors_base.published_layers import register_layer
from connectors_file_source.pmtiles import build_pmtiles, geojson_bbox, iceberg_table_to_geojson, upload_pmtiles
from dagster import AssetExecutionContext, MaterializeResult, asset

from platform_orchestration.assets.communes_boundaries import communes_boundaries

DATASET_ID = "communes_boundaries"
TABLE_IDENTIFIER = "bronze.communes_boundaries"
ID_PROPERTY = "commune_code"


@asset(key_prefix="serving", name="communes_boundaries_pmtiles", deps=[communes_boundaries])
def communes_boundaries_pmtiles(context: AssetExecutionContext) -> MaterializeResult:
    geojson = iceberg_table_to_geojson(TABLE_IDENTIFIER, id_property=ID_PROPERTY)

    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / f"{DATASET_ID}.pmtiles"
        build_pmtiles(geojson, layer_name=DATASET_ID, output_path=output_path)
        pmtiles_path = upload_pmtiles(output_path, DATASET_ID)

    bbox = geojson_bbox(geojson)
    from connectors_file_source.pmtiles import MAX_ZOOM, MIN_ZOOM

    register_layer(
        layer_id=DATASET_ID,
        source_dataset_id=DATASET_ID,
        pmtiles_path=pmtiles_path,
        bbox=bbox,
        min_zoom=MIN_ZOOM,
        max_zoom=MAX_ZOOM,
        id_property=ID_PROPERTY,
    )

    context.log.info(f"Published {pmtiles_path} ({len(geojson['features'])} features)")

    return MaterializeResult(
        metadata={
            "pmtiles_path": pmtiles_path,
            "feature_count": len(geojson["features"]),
            "bbox": str(bbox),
        }
    )
