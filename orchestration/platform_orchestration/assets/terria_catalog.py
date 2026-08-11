"""M7b — Generated TerriaMap catalog.

Reads published-layers registry, STAC API, and recipe manifests to produce
a Terria v8 init file (geodata.json).  Writes it to a shared volume that
TerriaMap serves from /app/wwwroot/init/, and also to S3 as backup.

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
SEAWEEDFS_ENDPOINT = os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333")
TERRIA_INIT_DIR = os.environ.get("TERRIA_INIT_DIR", "/opt/dagster/app/terria-init")

RECIPE_DIRS = [
    "recipes/datasets",
    "recipes/gee",
]

TERRIA_GROUPS = {
    "Boundaries": "Administrative boundary layers",
    "Indicators": "Socio-economic indicator datasets",
    "Earth Observation": "Satellite-derived products",
    "Alternative Data": "External open-data layers (WMS/WMTS)",
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
    ds_id = manifest.get("id", "")
    parts = [manifest.get("description", "")]
    gov = manifest.get("governance", {})
    if gov.get("caveats"):
        parts.append(f"\n\n**Limitations:** {gov['caveats']}")
    if gov.get("license"):
        parts.append(f"\n\n**License:** {gov['license']}")
    if gov.get("owner"):
        parts.append(f" | **Owner:** {gov['owner']}")
    if ds_id:
        parts.append(
            f'\n\n<a href="http://localhost:8080/dataset/{ds_id}"'
            f' target="_blank">View in Portal</a>'
        )
    return "".join(parts).strip()


def _build_vector_member(
    layer: dict[str, Any], manifest: dict[str, Any] | None
) -> dict[str, Any]:
    name = manifest.get("title", layer["layer_id"]) if manifest else layer["layer_id"]
    desc = _make_description(manifest) if manifest else ""
    geojson_url = (
        f"proxy/{SEAWEEDFS_ENDPOINT}/{SERVING_BUCKET}"
        f"/geojson/{layer['layer_id']}.geojson"
    )

    return {
        "type": "geojson",
        "id": layer["layer_id"],
        "name": name,
        "description": desc,
        "url": geojson_url,
        "opacity": 0.6,
    }


def _build_raster_member(
    dataset_id: str, manifest: dict[str, Any], stac_collections: list[dict]
) -> dict[str, Any] | None:
    zonal_id = f"{dataset_id.replace('_composite', '')}_zonal_stats"
    try:
        s3 = _s3()
        s3.head_object(Bucket=SERVING_BUCKET, Key=f"geojson/{zonal_id}.geojson")
    except Exception:
        return None
    geojson_url = (
        f"proxy/{SEAWEEDFS_ENDPOINT}/{SERVING_BUCKET}"
        f"/geojson/{zonal_id}.geojson"
    )
    return {
        "type": "geojson",
        "id": zonal_id,
        "name": manifest.get("title", dataset_id),
        "description": _make_description(manifest),
        "url": geojson_url,
    }


def _build_tabular_member(
    dataset_id: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    csv_url = (
        f"proxy/{SEAWEEDFS_ENDPOINT}/{SERVING_BUCKET}"
        f"/csv/{dataset_id}.csv"
    )
    return {
        "type": "csv",
        "id": dataset_id,
        "name": manifest.get("title", dataset_id),
        "description": _make_description(manifest),
        "url": csv_url,
    }


def _generate_region_ids(context: AssetExecutionContext) -> None:
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


def _external_layers() -> list[dict[str, Any]]:
    """Free public WMS layers — real alternative data, no auth needed."""
    gibs = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
    return [
        {
            "type": "wms",
            "id": "modis_ndvi",
            "name": "NDVI Végétation (MODIS Terra)",
            "description": (
                "Indice de végétation NDVI 8 jours — santé des cultures et "
                "couvert végétal, résolution ~250 m."
                '\n\n<b>Source:</b> NASA GIBS — '
                '<a href="https://earthdata.nasa.gov" target="_blank">'
                "earthdata.nasa.gov</a>"
            ),
            "url": gibs,
            "layers": "MODIS_Terra_NDVI_8Day",
            "opacity": 0.7,
        },
        {
            "type": "wms",
            "id": "worldcover_landuse",
            "name": "Occupation du Sol (ESA WorldCover)",
            "description": (
                "Carte d'occupation du sol 2021 à 10 m — cultures, forêt, "
                "urbain, eau, sols nus. Basée sur Sentinel-1 et Sentinel-2."
                '\n\n<b>Source:</b> ESA via Terrascope — '
                '<a href="https://esa-worldcover.org" target="_blank">'
                "esa-worldcover.org</a>"
            ),
            "url": "https://services.terrascope.be/wms/v2",
            "layers": "WORLDCOVER_2021_MAP",
            "opacity": 0.6,
        },
        {
            "type": "wms",
            "id": "gpm_precipitation",
            "name": "Précipitations (GPM NASA)",
            "description": (
                "Précipitations mensuelles cumulées — pluviométrie globale "
                "issue du satellite GPM (Global Precipitation Measurement)."
                '\n\n<b>Source:</b> NASA GIBS — '
                '<a href="https://gpm.nasa.gov" target="_blank">'
                "gpm.nasa.gov</a>"
            ),
            "url": gibs,
            "layers": "GPM_3IMERGM",
            "opacity": 0.6,
        },
        {
            "type": "wms",
            "id": "modis_lst",
            "name": "Température de Surface (MODIS Terra)",
            "description": (
                "Température de surface terrestre diurne mensuelle — "
                "stress thermique des cultures et îlots de chaleur."
                '\n\n<b>Source:</b> NASA GIBS — '
                '<a href="https://earthdata.nasa.gov" target="_blank">'
                "earthdata.nasa.gov</a>"
            ),
            "url": gibs,
            "layers": "MODIS_Terra_Land_Surface_Temp_Day_Monthly",
            "opacity": 0.7,
        },
        {
            "type": "wms",
            "id": "smap_soil_moisture",
            "name": "Humidité du Sol (SMAP)",
            "description": (
                "Humidité de la zone racinaire analysée — indicateur clé "
                "pour l'irrigation et la détection de sécheresse."
                '\n\n<b>Source:</b> NASA SMAP — '
                '<a href="https://smap.jpl.nasa.gov" target="_blank">'
                "smap.jpl.nasa.gov</a>"
            ),
            "url": gibs,
            "layers": "SMAP_L4_Analyzed_Root_Zone_Moisture",
            "opacity": 0.6,
        },
        {
            "type": "wms",
            "id": "modis_evapotranspiration",
            "name": "Évapotranspiration (MODIS Terra)",
            "description": (
                "Évapotranspiration mensuelle — bilan hydrique des cultures, "
                "besoins en eau et productivité végétale."
                '\n\n<b>Source:</b> NASA GIBS — '
                '<a href="https://earthdata.nasa.gov" target="_blank">'
                "earthdata.nasa.gov</a>"
            ),
            "url": gibs,
            "layers": "MODIS_Terra_Gross_Primary_Productivity_8Day",
            "opacity": 0.6,
        },
        {
            "type": "wms",
            "id": "viirs_active_fires",
            "name": "Feux Actifs (VIIRS)",
            "description": (
                "Anomalies thermiques détectées par VIIRS — feux de "
                "végétation actifs et risque d'incendie."
                '\n\n<b>Source:</b> NASA GIBS — '
                '<a href="https://earthdata.nasa.gov" target="_blank">'
                "earthdata.nasa.gov</a>"
            ),
            "url": gibs,
            "layers": "VIIRS_SNPP_Thermal_Anomalies",
            "opacity": 0.8,
        },
    ]


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

    groups["Alternative Data"] = _external_layers()

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
        "viewerMode": "2d",
    }

    catalog_json = json.dumps(catalog, indent=2, ensure_ascii=False)

    s3 = _s3()
    s3.put_object(
        Bucket=SERVING_BUCKET,
        Key="terria/catalog.json",
        Body=catalog_json.encode("utf-8"),
        ContentType="application/json",
    )

    init_dir = Path(TERRIA_INIT_DIR)
    if init_dir.is_dir():
        init_path = init_dir / "geodata.json"
        init_path.write_text(catalog_json, encoding="utf-8")
        context.log.info(f"Wrote init file to {init_path}")

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
