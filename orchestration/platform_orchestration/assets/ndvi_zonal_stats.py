"""M4 gold asset: zonal statistics of Dataset C (ndvi_composite COGs) over
Dataset B (communes_boundaries polygons) -> gold.ndvi_zonal_stats.

Reads the boundary polygons straight from their V2-bridge WKB column and
masks each period's COG with them via `rasterio.mask`, rather than a
dedicated zonal-stats library — one fewer dependency for what's a
straightforward per-polygon mean.
"""

import os

import boto3
import numpy as np
import pyarrow as pa
import rasterio
from connectors_base.catalog import get_catalog
from dagster import AssetExecutionContext, MaterializeResult, asset
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError
from rasterio.mask import mask as rio_mask
from shapely import wkb
from shapely.geometry import mapping

from platform_orchestration.assets.communes_boundaries import communes_boundaries
from platform_orchestration.assets.ndvi_composite import ndvi_composite

GOLD_TABLE_IDENTIFIER = "gold.ndvi_zonal_stats"
GOLD_SCHEMA = pa.schema(
    [
        ("period", pa.string()),
        ("commune_code", pa.string()),
        ("mean_ndvi", pa.float64()),
        ("pixel_count", pa.int64()),
    ]
)

SERVING_BUCKET = "serving"


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333"),
        aws_access_key_id=os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
        aws_secret_access_key=os.environ.get(
            "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
        ),
        region_name="local-01",
    )


def _list_cog_periods(dataset_id: str) -> list[str]:
    prefix = f"cog/{dataset_id}/"
    resp = _s3_client().list_objects_v2(Bucket=SERVING_BUCKET, Prefix=prefix)
    periods = []
    for obj in resp.get("Contents", []):
        name = obj["Key"][len(prefix):]
        if name.endswith(".tif"):
            periods.append(name[: -len(".tif")])
    return sorted(periods)


@asset(key_prefix="gold", name="ndvi_zonal_stats", deps=[communes_boundaries, ndvi_composite])
def ndvi_zonal_stats(context: AssetExecutionContext) -> MaterializeResult:
    catalog = get_catalog()
    boundaries = catalog.load_table("bronze.communes_boundaries").scan().to_arrow().to_pylist()

    periods = _list_cog_periods("ndvi_composite")
    if not periods:
        raise RuntimeError(
            "no ndvi_composite COGs found under s3://serving/cog/ndvi_composite/ — "
            "materialize serving/ndvi_composite first"
        )

    rows = []
    for period in periods:
        cog_url = f"/vsicurl/http://seaweedfs:8333/{SERVING_BUCKET}/cog/ndvi_composite/{period}.tif"
        with rasterio.open(cog_url) as src:
            for commune in boundaries:
                geom = wkb.loads(commune["geometry"])
                try:
                    out_image, _ = rio_mask(src, [mapping(geom)], crop=True, nodata=np.nan)
                except ValueError:
                    continue  # commune's footprint doesn't overlap this raster
                data = out_image[0]
                valid = data[~np.isnan(data)]
                if valid.size == 0:
                    continue
                rows.append(
                    {
                        "period": period,
                        "commune_code": commune["commune_code"],
                        "mean_ndvi": float(valid.mean()),
                        "pixel_count": int(valid.size),
                    }
                )

    table = pa.Table.from_pylist(rows, schema=GOLD_SCHEMA)

    try:
        catalog.create_namespace("gold")
    except NamespaceAlreadyExistsError:
        pass
    try:
        gold_table = catalog.create_table(GOLD_TABLE_IDENTIFIER, schema=GOLD_SCHEMA)
    except TableAlreadyExistsError:
        gold_table = catalog.load_table(GOLD_TABLE_IDENTIFIER)
    gold_table.overwrite(table)

    context.log.info(
        f"Computed zonal stats for {len(periods)} period(s) x {len(boundaries)} "
        f"communes -> {len(rows)} rows"
    )
    return MaterializeResult(metadata={"row_count": len(rows), "periods": periods})
