"""Dataset C: `gee_source` connector, recipe interpreter entry point.

Runs entirely against `sample-data/gee_fixtures/` (provenance.mode =
"fixture", no Earth Engine credentials needed) using "Path B" — straight
from the in-process composite array to a COG on SeaweedFS, no GCS staging
bucket (MASTER_PROMPT M4).

Each period in the fixture's scene catalog is checked independently
against its last-published contributing-asset hash. A period whose asset
set hasn't changed is skipped entirely — no COG rewrite, no STAC update,
no new `PipelineRun` row. This is the set-difference change detection
STOP GATE 4 requires: forcing a late-arriving scene into one period's
entry in `scenes_catalog.json` causes exactly that period to reappear in
`run()`'s return value on the next call.
"""

from __future__ import annotations

import json
import tempfile
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
from connectors_base.checksum import sha256_bytes
from connectors_base.pipeline_run import PipelineRunRecorder
from connectors_base.quality import QualityContext, run_checks
from connectors_base.repo_paths import repo_root
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from connectors_gee_source import contributing_assets, stac
from connectors_gee_source.cog import get_s3_client, upload_cog, write_cog
from connectors_gee_source.interpreter import run_period
from connectors_gee_source.recipe import GeeRecipe, load_recipe

SUMMARY_SCHEMA = pa.schema(
    [
        ("dataset_id", pa.string()),
        ("period", pa.string()),
        ("pixel_count", pa.int64()),
        ("mean_value", pa.float64()),
        ("min_value", pa.float64()),
        ("max_value", pa.float64()),
    ]
)

RAW_BUCKET = "raw"


def _aoi_geometry_and_bbox(recipe: GeeRecipe):
    aoi_path = repo_root() / recipe.domain.aoi
    geojson = json.loads(aoi_path.read_text(encoding="utf-8"))
    geoms = [shape(f["geometry"]) for f in geojson["features"]]
    union = unary_union(geoms)
    return mapping(union.convex_hull), union.bounds


def _period_bounds(period: str, grain: str) -> tuple[datetime, datetime]:
    if grain != "month":
        raise NotImplementedError(f"grain={grain!r} not implemented in the POC connector")
    year, month = (int(p) for p in period.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _s3_upload_json(client, key: str, payload: dict | list) -> None:
    import io

    body = json.dumps(payload).encode("utf-8")
    client.upload_fileobj(io.BytesIO(body), RAW_BUCKET, key)


def _use_real_gee() -> bool:
    try:
        from connectors_gee_source.gee_client import is_available
        return is_available()
    except ImportError:
        return False


def _load_scene_catalog(recipe: GeeRecipe, geometry: dict, bbox: tuple) -> dict[str, list[str]]:
    if _use_real_gee():
        from connectors_gee_source.gee_client import list_scene_ids
        from datetime import date
        today = date.today()
        catalog: dict[str, list[str]] = {}
        year, month = today.year, today.month
        for offset in range(6):
            m = month - offset
            y = year
            while m <= 0:
                m += 12
                y -= 1
            period = f"{y}-{m:02d}"
            from calendar import monthrange
            last_day = monthrange(y, m)[1]
            start = f"{y}-{m:02d}-01"
            end = f"{y}-{m:02d}-{last_day:02d}"
            try:
                ids = list_scene_ids(geometry, start, end)
                if ids:
                    catalog[period] = ids
            except Exception:
                continue
        return catalog
    else:
        from connectors_gee_source import fixtures
        return fixtures.load_scene_catalog()


def run(recipe_path: str | Path) -> list[PipelineRunRecorder]:
    recipe = load_recipe(recipe_path)
    geometry, bbox = _aoi_geometry_and_bbox(recipe)
    catalog = _load_scene_catalog(recipe, geometry, bbox)

    collection_id = recipe.publish.stac_collection or recipe.id
    stac.ensure_collection(
        collection_id=collection_id,
        title=recipe.title,
        description=recipe.description,
        license=recipe.governance.license,
        bbox=bbox,
        temporal_start=_period_bounds(min(catalog), recipe.temporal.grain)[0],
    )

    reprocessed: list[PipelineRunRecorder] = []
    for period in sorted(catalog):
        asset_ids = catalog[period]
        new_hash = contributing_assets.hash_asset_ids(asset_ids)
        old_hash = contributing_assets.latest_hash(recipe.id, period)
        if old_hash == new_hash:
            continue  # set-difference detection: this period is unchanged

        reprocessed.append(
            _process_period(recipe, period, asset_ids, bbox, geometry, collection_id, new_hash)
        )

    return reprocessed


def _process_period(
    recipe: GeeRecipe,
    period: str,
    asset_ids: list[str],
    bbox: tuple[float, float, float, float],
    geometry: dict,
    collection_id: str,
    asset_hash: str,
) -> PipelineRunRecorder:
    period_start, period_end = _period_bounds(period, recipe.temporal.grain)
    period_manifest = recipe.model_copy(update={"id": f"{recipe.id}:{period}"})

    with PipelineRunRecorder(period_manifest) as run_record:
        # --- output 1: raw artifact (contributing-asset list) + checksum ----
        s3 = get_s3_client()
        scene_ids_payload = {"period": period, "asset_ids": sorted(asset_ids)}
        checksum = sha256_bytes(json.dumps(scene_ids_payload, sort_keys=True).encode("utf-8"))
        raw_key = f"{recipe.id}/{run_record.run_id}/scene_ids.json"
        _s3_upload_json(s3, raw_key, scene_ids_payload)
        run_record.record_raw_artifact(f"s3://{RAW_BUCKET}/{raw_key}", checksum)

        # --- run the recipe interpreter over this period's scenes -----------
        composite = run_period(recipe, asset_ids)

        # --- output 2: normalised asset (COG) --------------------------------
        with tempfile.TemporaryDirectory() as tmp:
            cog_path = Path(tmp) / f"{period}.tif"
            write_cog(composite, bbox, recipe.domain.crs, cog_path)
            cog_href = upload_cog(cog_path, recipe.id, period)
        run_record.record_normalised_asset(cog_href, "cog")
        run_record.record_row_count(int(composite.size))

        # --- output 3: catalog registration (STAC item) ----------------------
        mode = "real GEE" if _use_real_gee() else "fixture"
        provenance_sentence = (
            f"{recipe.temporal.reduction.type}-{recipe.temporal.reduction.p} NDVI from "
            f"{len(asset_ids)} cloud-masked scenes, computed under recipe {recipe.id} "
            f"({mode})"
            if recipe.temporal.reduction.type == "percentile"
            else f"{recipe.temporal.reduction.type} NDVI from {len(asset_ids)} scenes "
            f"({mode})"
        )
        item_id = f"{recipe.id}_{period}"
        stac.publish_item(
            collection_id=collection_id,
            item_id=item_id,
            bbox=bbox,
            geometry=geometry,
            period_start=period_start,
            period_end=period_end,
            cog_href=cog_href,
            recipe_id=recipe.id,
            contributing_assets=asset_ids,
            contributing_assets_hash=asset_hash,
            provenance_sentence=provenance_sentence,
        )
        stac_href = f"{stac.stac_api_url()}/collections/{collection_id}/items/{item_id}"
        run_record.record_catalog_registration(f"stac:{collection_id}/{item_id}", stac_href)

        # --- output 4: quality report (on a summary row, not raw pixels) -----
        summary = pa.table(
            {
                "dataset_id": [recipe.id],
                "period": [period],
                "pixel_count": [int(composite.size)],
                "mean_value": [float(composite.mean())],
                "min_value": [float(composite.min())],
                "max_value": [float(composite.max())],
            },
            schema=SUMMARY_SCHEMA,
        )
        passed, report = run_checks(
            summary,
            table_name=f"{recipe.id}_{period}_summary".replace("-", "_"),
            checks=recipe.quality.checks,
            ctx=QualityContext(
                expected_schema=SUMMARY_SCHEMA,
                value_ranges={"mean_value": (-1.0, 1.0), "min_value": (-1.0, 1.0), "max_value": (-1.0, 1.0)},
            ),
        )
        run_record.record_quality_report(passed, report)

        # record the contributing-asset manifest last, only once everything
        # else about this period succeeded
        contributing_assets.record(recipe.id, period, asset_ids)

    return run_record
