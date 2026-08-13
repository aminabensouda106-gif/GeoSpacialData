from dagster import Definitions, load_assets_from_modules

from platform_orchestration.assets import (
    communes_boundaries,
    communes_boundaries_pmtiles,
    hello,
    ndvi_composite,
    ndvi_zonal_stats,
    osm_health_facilities,
    terria_catalog,
)
from platform_orchestration.assets.quality_checks import (
    communes_boundaries_quality,
)

all_assets = load_assets_from_modules(
    [
        hello,
        communes_boundaries,
        communes_boundaries_pmtiles,
        ndvi_composite,
        ndvi_zonal_stats,
        osm_health_facilities,
        terria_catalog,
    ]
)

defs = Definitions(
    assets=all_assets,
    asset_checks=[communes_boundaries_quality],
)
