from dagster import Definitions, load_assets_from_modules

from platform_orchestration.assets import hello

all_assets = load_assets_from_modules([hello])

defs = Definitions(assets=all_assets)
