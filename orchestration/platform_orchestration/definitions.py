from dagster import Definitions, load_assets_from_modules

from platform_orchestration.assets import (
    communes_boundaries,
    communes_boundaries_pmtiles,
    employment_indicators,
    hello,
)
from platform_orchestration.assets.quality_checks import (
    communes_boundaries_quality,
    employment_indicators_quality,
)

all_assets = load_assets_from_modules(
    [hello, employment_indicators, communes_boundaries, communes_boundaries_pmtiles]
)

defs = Definitions(
    assets=all_assets,
    asset_checks=[employment_indicators_quality, communes_boundaries_quality],
)
