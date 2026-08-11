"""The recipe interpreter: runs a `GeeRecipe`'s ordered `steps` over a
period's scenes. Uses real Google Earth Engine when credentials are
available, otherwise falls back to fixture data.
"""

import numpy as np

from connectors_gee_source.ops import get_op
from connectors_gee_source.recipe import GeeRecipe


def _use_real_gee() -> bool:
    try:
        from connectors_gee_source.gee_client import is_available
        return is_available()
    except ImportError:
        return False


def run_period(recipe: GeeRecipe, asset_ids: list[str]) -> np.ndarray:
    if _use_real_gee():
        return _run_period_real(recipe, asset_ids)
    return _run_period_fixture(recipe, asset_ids)


def _run_period_fixture(recipe: GeeRecipe, asset_ids: list[str]) -> np.ndarray:
    from connectors_gee_source import fixtures

    scenes = [fixtures.generate_scene(asset_id) for asset_id in asset_ids]
    per_scene_arrays: list[np.ndarray] | None = None

    for step in recipe.steps:
        op = get_op(step.op)
        if op.kind == "scene_transform":
            scenes = [op.fn(scene, **step.params) for scene in scenes]
        elif op.kind == "scene_to_array":
            per_scene_arrays = [op.fn(scene, **step.params) for scene in scenes]
        elif op.kind == "temporal_reduce":
            if per_scene_arrays is None:
                raise RuntimeError(
                    f"step {step.id!r} (op={step.op!r}) ran before any "
                    "scene_to_array step"
                )
            per_scene_arrays = [op.fn(per_scene_arrays, **step.params)]

    if per_scene_arrays is None or len(per_scene_arrays) != 1:
        raise RuntimeError("recipe did not converge to a single composite")
    return per_scene_arrays[0]


def _run_period_real(recipe: GeeRecipe, asset_ids: list[str]) -> np.ndarray:
    """Server-side GEE computation: cloud mask → NDVI → temporal reduce.

    Returns the composite as a numpy array. The heavy computation runs on
    GEE servers; we only download the final result.
    """
    from connectors_gee_source.gee_client import compute_composite
    import json
    from connectors_base.repo_paths import repo_root

    aoi_path = repo_root() / recipe.domain.aoi
    geojson = json.loads(aoi_path.read_text(encoding="utf-8"))
    from shapely.geometry import shape
    from shapely.ops import unary_union

    geoms = [shape(f["geometry"]) for f in geojson["features"]]
    union = unary_union(geoms)
    from shapely.geometry import mapping
    aoi_geojson = mapping(union.convex_hull)

    period_parts = asset_ids[0].split("_") if asset_ids else []
    period = None
    for part in period_parts:
        if len(part) == 7 and "-" in part:
            period = part
            break

    if period is None:
        period = recipe.id

    year, month = (int(p) for p in period.split("-")) if "-" in period else (2024, 1)
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day:02d}"

    reducer = recipe.temporal.reduction.type
    p = recipe.temporal.reduction.p

    array, bbox, scene_count = compute_composite(
        aoi_geojson=aoi_geojson,
        start_date=start_date,
        end_date=end_date,
        reducer_type=reducer,
        percentile=p or 90,
        scale_m=recipe.domain.scale_m,
    )
    return array
