"""M7b — Generated TerriaMap catalog.

Reads STAC API collections/items, published-layers registry, and manifest
metadata to produce a Terria v8 init file (catalog.json).  Writes it to
s3://serving/terria/catalog.json so TerriaMap picks it up via its proxy.

Also generates regionIds JSON files for region mapping (M7c).
"""

import json
import os
from pathlib import Path
from typing import Any

import boto3
import httpx
import yaml
from dagster import AssetExecutionContext, MaterializeResult, asset

SERVING_BUCKET = "serving"
STAC_API_URL = os.environ.get("STAC_API_URL", "http://stac-api:8080")
TITILER_URL = os.environ.get("TITILER_URL", "http://titiler:80")
SEAWEEDFS_ENDPOINT = os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333")

RECIPE_DIRS = [
    "recipes/datasets",
    "recipes/gee",
]

TERRIA_GROUPS = {
    "Boundaries": "Administrative boundary layers",
    "Indicators": "Socio-economic indicator datasets",
    "Earth Observation": "Satellite-derived products",
}

GROUP_MAP = {
    "vector": "Boundaries",
    "tabular": "Indicators",
    "raster": "Earth Observation",
}


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=SEAWEEDFS_ENDPOINT,
        aws_access_key_id=os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
        aws_secret_access_key=os.environ.get(
            "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
        ),
        region_name="us-east-1",
    )


def _repo_root() -> Path:
    return Path(os.environ.get("PLATFORM_REPO_ROOT", "/opt/dagster/app"))


def _load_manifests() -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    for d in RECIPE_DIRS:
        recipe_dir = _repo_root() / d
        if not recipe_dir.is_dir():
            continue
        for f in sorted(recipe_dir.glob("*.yaml")):
            with open(f) as fh:
                m = yaml.safe_load(fh)
                manifests[m["id"]] = m
    return manifests


def _load_published_layers() -> list[dict[str, Any]]:
    try:
        from connectors_base.catalog import get_catalog

        catalog = get_catalog()
        table = catalog.load_table("platform.published_layers")
        return table.scan().to_arrow().to_pylist()
    except Exception:
        return []


def _load_stac_collections() -> list[dict[str, Any]]:
    try:
        resp = httpx.get(f"{STAC_API_URL}/collections", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("collections", [])
    except Exception:
        pass
    return []


def _make_description(manifest: dict[str, Any]) -> str:
    parts = [manifest.get("description", "")]
    gov = manifest.get("governance", {})
    if gov.get("caveats"):
        parts.append(f"\n\n**Limitations:** {gov['caveats']}")
    if gov.get("license"):
        parts.append(f"\n\n**License:** {gov['license']}")
    if gov.get("owner"):
        parts.append(f" | **Owner:** {gov['owner']}")
    return "".join(parts).strip()


def _build_raster_member(
    dataset_id: str, manifest: dict[str, Any], stac_collections: list[dict]
) -> dict[str, Any] | None:
    collection = next(
        (c for c in stac_collections if c["id"] == dataset_id),
        None,
    )
    stac_coll = manifest.get("publish", {}).get("stac_collection", dataset_id)
    collection = collection or next(
        (c for c in stac_collections if c["id"] == stac_coll), None
    )
    if not collection:
        return None

    return {
        "type": "ckan-item",
        "id": dataset_id,
        "name": manifest.get("title", dataset_id),
        "description": _make_description(manifest),
        "url": f"proxy/{STAC_API_URL}/collections/{collection['id']}/items",
        "info": [
            {
                "name": "Data Governance",
                "content": _make_description(manifest),
            }
        ],
    }


def _build_vector_member(
    layer: dict[str, Any], manifest: dict[str, Any] | None
) -> dict[str, Any]:
    name = manifest.get("title", layer["layer_id"]) if manifest else layer["layer_id"]
    desc = _make_description(manifest) if manifest else ""
    pmtiles_url = f"proxy/{SEAWEEDFS_ENDPOINT}/{SERVING_BUCKET}/{layer['pmtiles_path']}"

    return {
        "type": "mvt",
        "id": layer["layer_id"],
        "name": name,
        "description": desc,
        "url": pmtiles_url,
        "opacity": 0.6,
        "rectangle": {
            "west": layer["bbox_minx"],
            "south": layer["bbox_miny"],
            "east": layer["bbox_maxx"],
            "north": layer["bbox_maxy"],
        },
    }


def _build_tabular_member(
    dataset_id: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    return {
        "type": "group",
        "id": dataset_id,
        "name": manifest.get("title", dataset_id),
        "description": _make_description(manifest),
        "members": [],
        "info": [
            {
                "name": "Access",
                "content": f"View in [Portal Workbench](http://localhost:8080/datasets/{dataset_id})",
            }
        ],
    }


def _generate_region_ids(context: AssetExecutionContext) -> None:
    """Generate regionIds JSON files for TerriaMap region mapping."""
    try:
        from connectors_base.catalog import get_catalog

        catalog = get_catalog()
        boundaries = (
            catalog.load_table("bronze.communes_boundaries").scan().to_arrow()
        )
        codes = boundaries.column("commune_code").to_pylist()
        names = boundaries.column("commune_name").to_pylist()

        s3 = _s3()
        s3.put_object(
            Bucket=SERVING_BUCKET,
            Key="terria/regionids/communes_boundaries.json",
            Body=json.dumps({"values": codes, "layer": "communes_boundaries"}),
            ContentType="application/json",
        )
        s3.put_object(
            Bucket=SERVING_BUCKET,
            Key="terria/regionids/communes_boundaries_names.json",
            Body=json.dumps({"values": names, "layer": "communes_boundaries"}),
            ContentType="application/json",
        )
        context.log.info(
            f"Generated regionIds: {len(codes)} codes, {len(names)} names"
        )
    except Exception as e:
        context.log.warning(f"Could not generate regionIds: {e}")


@asset(key_prefix="serving", name="terria_catalog")
def terria_catalog(context: AssetExecutionContext) -> MaterializeResult:
    manifests = _load_manifests()
    published_layers = _load_published_layers()
    stac_collections = _load_stac_collections()

    groups: dict[str, list[dict[str, Any]]] = {
        name: [] for name in TERRIA_GROUPS
    }

    group_names_lower = {k.lower(): k for k in TERRIA_GROUPS}

    def _resolve_group(raw: str | None, fallback: str) -> str:
        if not raw:
            return fallback
        return group_names_lower.get(raw.lower(), fallback)

    for layer in published_layers:
        ds_id = layer.get("source_dataset_id", layer["layer_id"])
        manifest = manifests.get(ds_id)
        member = _build_vector_member(layer, manifest)
        raw_group = manifest.get("publish", {}).get("terria_group") if manifest else None
        group_name = _resolve_group(raw_group, "Boundaries")
        groups[group_name].append(member)

    for ds_id, manifest in manifests.items():
        modality = manifest.get("target", {}).get("modality", "")
        raw_group = manifest.get("publish", {}).get("terria_group")
        default_group = GROUP_MAP.get(modality, "Earth Observation")

        if modality == "raster":
            member = _build_raster_member(ds_id, manifest, stac_collections)
            if member:
                groups.setdefault(
                    _resolve_group(raw_group, default_group), []
                ).append(member)

        elif modality == "tabular":
            member = _build_tabular_member(ds_id, manifest)
            groups.setdefault(
                _resolve_group(raw_group, default_group), []
            ).append(member)

    catalog_members = []
    for group_name, group_desc in TERRIA_GROUPS.items():
        members = groups.get(group_name, [])
        if members:
            catalog_members.append(
                {
                    "type": "group",
                    "id": group_name.lower().replace(" ", "_"),
                    "name": group_name,
                    "description": group_desc,
                    "members": members,
                }
            )

    catalog = {
        "catalog": catalog_members,
        "homeCamera": {
            "west": -10,
            "south": 27,
            "east": 0,
            "north": 36,
        },
    }

    catalog_json = json.dumps(catalog, indent=2, ensure_ascii=False)

    s3 = _s3()
    s3.put_object(
        Bucket=SERVING_BUCKET,
        Key="terria/catalog.json",
        Body=catalog_json.encode("utf-8"),
        ContentType="application/json",
    )

    _generate_region_ids(context)

    member_count = sum(len(m) for m in groups.values())
    context.log.info(
        f"Generated Terria catalog: {len(catalog_members)} groups, "
        f"{member_count} members, {len(published_layers)} layers, "
        f"{len(stac_collections)} STAC collections"
    )

    return MaterializeResult(
        metadata={
            "group_count": len(catalog_members),
            "member_count": member_count,
            "published_layer_count": len(published_layers),
            "stac_collection_count": len(stac_collections),
        }
    )
