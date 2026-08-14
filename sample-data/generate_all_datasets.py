"""Generates synthetic agricultural/terrestrial CSVs for the 11 POC communes
and uploads each as a flat Parquet file to s3://serving/cube/<id>.parquet on
SeaweedFS, which is where semantic/cubes/*.yml's DuckDB reader expects to
find them (see semantic/cubes/ndvi_zonal_stats.yml for the existing pattern).

Run once, against a running `seaweedfs` container:

    python sample-data/generate_all_datasets.py

All values are synthetic and seeded for reproducibility — see each
manifest's `governance.caveats` in recipes/datasets/.
"""

from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).parent
PERIODS = [f"2024-{m:02d}" for m in range(1, 13)]
SEASONS = ["hiver", "printemps", "été", "automne"]
CROP_TYPES = ["Blé tendre", "Blé dur", "Orge", "Maïs", "Betterave sucrière", "Agrumes", "Maraîchage"]
IRRIGATION_TYPES = ["irrigué", "pluvial"]

SERVING_BUCKET = "serving"


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("SEAWEEDFS_ENDPOINT", "http://localhost:8333"),
        aws_access_key_id=os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
        aws_secret_access_key=os.environ.get(
            "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
        ),
        region_name="local-01",
    )


def _load_communes() -> list[dict]:
    with open(HERE / "communes_boundaries.geojson", encoding="utf-8") as f:
        gj = json.load(f)
    communes = []
    for feat in gj["features"]:
        props = feat["properties"]
        coords = feat["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        communes.append(
            {
                "commune_code": props["commune_code"],
                "commune_name": props["commune_name"],
                "lat": sum(lats) / len(lats),
                "lon": sum(lons) / len(lons),
            }
        )
    return communes


def _stable_hash(s: str) -> int:
    """`hash(str)` is randomized per-process (PYTHONHASHSEED) in Python 3,
    which would make the generated data non-reproducible across runs."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _lcg(seed: int):
    """Tiny deterministic PRNG (no numpy dependency) — linear congruential
    generator, good enough for synthetic demo data, reproducible across runs."""
    state = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    return rand


def _seasonal(month: int, peak_month: float, amplitude: float, baseline: float) -> float:
    phase = (month - peak_month) / 12.0 * 2 * math.pi
    return baseline + amplitude * math.cos(phase)


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _write_csv_and_parquet(dataset_id: str, rows: list[dict]) -> None:
    csv_path = HERE / f"{dataset_id}.csv"
    columns = list(rows[0].keys())

    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(str(row[c]) for c in columns))
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {csv_path} ({len(rows)} rows)")

    table = pa.table({c: [row[c] for row in rows] for c in columns})
    buf = io.BytesIO()
    pq.write_table(table, buf)
    buf.seek(0)

    key = f"cube/{dataset_id}.parquet"
    _s3_client().put_object(Bucket=SERVING_BUCKET, Key=key, Body=buf.getvalue())
    print(f"uploaded s3://{SERVING_BUCKET}/{key} ({len(rows)} rows)")


def generate_vegetation_indices(communes: list[dict]) -> list[dict]:
    rows = []
    for c in communes:
        rand = _lcg(_stable_hash(c["commune_code"]) & 0xFFFF)
        aridity = _clip((31.5 - c["lat"]) / 10.0 + 0.5, 0.0, 1.0)  # south = more arid
        for period in PERIODS:
            month = int(period.split("-")[1])
            seasonal = _clip(_seasonal(month, 4.5, 0.5, 0.5), 0.0, 1.0)
            ndvi = _clip(0.15 + 0.55 * seasonal * (1 - 0.3 * aridity) + 0.05 * (rand() - 0.5), 0.1, 0.8)
            evi = _clip(ndvi * 0.72 + 0.03 * (rand() - 0.5), 0.08, 0.58)
            savi = _clip(ndvi * 0.8 + 0.03 * (rand() - 0.5), 0.1, 0.62)
            ndwi = _clip(-0.3 + 0.7 * seasonal * (1 - aridity) + 0.05 * (rand() - 0.5), -0.35, 0.42)
            msavi2 = _clip(ndvi * 0.85 + 0.02 * (rand() - 0.5), 0.1, 0.65)
            lai = _clip(0.5 + 3.5 * ndvi + 0.2 * (rand() - 0.5), 0.4, 4.2)
            ndmi = _clip(-0.2 + 0.6 * seasonal * (1 - aridity) + 0.05 * (rand() - 0.5), -0.25, 0.4)
            rows.append({
                "commune_code": c["commune_code"],
                "period": period,
                "ndvi": round(ndvi, 4),
                "evi": round(evi, 4),
                "savi": round(savi, 4),
                "ndwi": round(ndwi, 4),
                "msavi2": round(msavi2, 4),
                "lai": round(lai, 3),
                "ndmi": round(ndmi, 4),
            })
    return rows


def generate_climate_indicators(communes: list[dict]) -> list[dict]:
    rows = []
    for c in communes:
        rand = _lcg((_stable_hash(c["commune_code"]) ^ 0x5A5A) & 0xFFFF)
        continentality = _clip((c["lon"] + 8.0) / 4.0, 0.0, 1.0)  # inland = wider swing
        for period in PERIODS:
            month = int(period.split("-")[1])
            temp_seasonal = _seasonal(month, 7.5, 1.0, 0.0)
            avg_temp = _clip(25.0 - (c["lat"] - 30.0) * 0.8 + temp_seasonal * (10 + 5 * continentality)
                              + 2 * (rand() - 0.5), 5.0, 45.0)
            spread = 6.0 + 3.0 * continentality
            min_temp = _clip(avg_temp - spread, 0.0, 40.0)
            max_temp = _clip(avg_temp + spread, 5.0, 46.0)

            wet_seasonal = _clip(_seasonal(month, 1.0, 0.5, 0.5), 0.0, 1.0)
            precip = _clip(110.0 * wet_seasonal * (1 - 0.2 * continentality) + 10 * (rand() - 0.5), 0.0, 120.0)

            et0 = _clip(2.0 + (avg_temp / 42.0) * 6.0 + (rand() - 0.5), 0.5, 9.0) * 30
            gdd = _clip((avg_temp - 5.0) * 30, 0.0, 900.0) if avg_temp > 5.0 else 0.0
            frost_days = int(_clip((5.0 - min_temp) * 3, 0, 20)) if min_temp < 5.0 else 0
            spi = _clip((precip - 55.0) / 35.0, -2.5, 2.5)

            rows.append({
                "commune_code": c["commune_code"],
                "period": period,
                "avg_temp_c": round(avg_temp, 1),
                "min_temp_c": round(min_temp, 1),
                "max_temp_c": round(max_temp, 1),
                "precipitation_mm": round(precip, 1),
                "et0_mm": round(et0, 1),
                "gdd": round(gdd, 1),
                "frost_days": frost_days,
                "spi_index": round(spi, 2),
            })
    return rows


def generate_soil_properties(communes: list[dict]) -> list[dict]:
    rows = []
    for c in communes:
        rand = _lcg((_stable_hash(c["commune_code"]) ^ 0x1234) & 0xFFFF)
        aridity = _clip((31.5 - c["lat"]) / 10.0 + 0.5, 0.0, 1.0)
        base_ph = 6.5 + 2.0 * aridity  # more alkaline in arid zones
        base_clay = 20 + 15 * rand()
        base_silt = 25 + 10 * rand()
        base_sand = max(10.0, 100 - base_clay - base_silt)
        for period in PERIODS:
            noise = (rand() - 0.5)
            rows.append({
                "commune_code": c["commune_code"],
                "period": period,
                "ph": round(_clip(base_ph + 0.1 * noise, 6.5, 8.5), 2),
                "organic_matter_pct": round(_clip(2.5 - 1.5 * aridity + 0.3 * noise, 0.3, 3.5), 2),
                "nitrogen_kg_ha": round(_clip(80 - 30 * aridity + 10 * noise, 20, 120), 1),
                "phosphorus_mg_kg": round(_clip(18 + 8 * noise, 4, 45), 1),
                "potassium_mg_kg": round(_clip(220 + 60 * noise, 80, 420), 1),
                "clay_pct": round(base_clay, 1),
                "silt_pct": round(base_silt, 1),
                "sand_pct": round(base_sand, 1),
                "water_retention_mm": round(_clip(140 - 60 * aridity + 15 * noise, 40, 180), 1),
                "ec_ds_m": round(_clip(0.5 + 1.5 * aridity + 0.2 * noise, 0.2, 3.5), 2),
            })
    return rows


def generate_water_resources(communes: list[dict]) -> list[dict]:
    rows = []
    for c in communes:
        rand = _lcg((_stable_hash(c["commune_code"]) ^ 0x9999) & 0xFFFF)
        aridity = _clip((31.5 - c["lat"]) / 10.0 + 0.5, 0.0, 1.0)
        base_irrigated_area = 800 + 2500 * rand()
        for period in PERIODS:
            month = int(period.split("-")[1])
            wet_seasonal = _clip(_seasonal(month, 1.0, 0.5, 0.5), 0.0, 1.0)
            rainfall = _clip(110.0 * wet_seasonal * (1 - 0.2 * aridity) + 10 * (rand() - 0.5), 0.0, 120.0)
            rows.append({
                "commune_code": c["commune_code"],
                "period": period,
                "groundwater_level_m": round(_clip(25 + 40 * aridity - 5 * wet_seasonal + 3 * (rand() - 0.5), 5, 90), 1),
                "river_flow_m3_s": round(_clip(15 * wet_seasonal * (1 - aridity) + 2 * rand(), 0.2, 40), 2),
                "dam_fill_rate_pct": round(_clip(30 + 50 * wet_seasonal * (1 - 0.3 * aridity) + 5 * (rand() - 0.5), 5, 95), 1),
                "irrigated_area_ha": round(base_irrigated_area, 0),
                "irrigation_efficiency_pct": round(_clip(55 + 25 * (1 - aridity) + 5 * (rand() - 0.5), 35, 90), 1),
                "rainfall_mm": round(rainfall, 1),
            })
    return rows


def generate_land_degradation(communes: list[dict]) -> list[dict]:
    rows = []
    for c in communes:
        rand = _lcg((_stable_hash(c["commune_code"]) ^ 0x4444) & 0xFFFF)
        aridity = _clip((31.5 - c["lat"]) / 10.0 + 0.5, 0.0, 1.0)
        for period in PERIODS:
            noise = (rand() - 0.5)
            rows.append({
                "commune_code": c["commune_code"],
                "period": period,
                "ldi": round(_clip(0.2 + 0.5 * aridity + 0.1 * noise, 0.1, 0.9), 2),
                "erosion_t_ha_yr": round(_clip(2 + 12 * aridity + 2 * noise, 0.5, 18), 2),
                "vegetation_loss_pct": round(_clip(3 + 15 * aridity + 3 * noise, 0, 35), 1),
                "salinity_ds_m": round(_clip(0.5 + 2.0 * aridity + 0.3 * noise, 0.2, 4.0), 2),
                "aridity_index": round(_clip(aridity + 0.05 * noise, 0.05, 0.95), 2),
            })
    return rows


def generate_crop_calendar(communes: list[dict]) -> list[dict]:
    rows = []
    for c in communes:
        rand = _lcg((_stable_hash(c["commune_code"]) ^ 0x7777) & 0xFFFF)
        aridity = _clip((31.5 - c["lat"]) / 10.0 + 0.5, 0.0, 1.0)
        for season in SEASONS:
            crop = CROP_TYPES[int(rand() * len(CROP_TYPES)) % len(CROP_TYPES)]
            irrigation = IRRIGATION_TYPES[int(rand() * len(IRRIGATION_TYPES)) % len(IRRIGATION_TYPES)]
            irrigated = irrigation == "irrigué"
            yield_q_ha = _clip(
                (30 if irrigated else 20) + 15 * (1 - aridity) * rand() - 5 * aridity, 15, 45
            )
            rows.append({
                "commune_code": c["commune_code"],
                "season": season,
                "crop_type": crop,
                "irrigation_type": irrigation,
                "sowing_date": f"2024-{'11' if season == 'automne' else '03'}-15",
                "harvest_date": f"2024-{'06' if season == 'automne' else '09'}-15",
                "yield_q_ha": round(yield_q_ha, 1),
                "cultivated_area_ha": round(200 + 1800 * rand(), 0),
                "water_consumption_m3_ha": round(_clip(3500 if irrigated else 600, 400, 6000)
                                                  + 500 * (rand() - 0.5), 1),
                "water_stress_index": round(_clip(0.2 + 0.6 * aridity * (0.5 if irrigated else 1.0)
                                                   + 0.1 * (rand() - 0.5), 0.05, 0.95), 2),
            })
    return rows


def main() -> None:
    communes = _load_communes()
    print(f"loaded {len(communes)} communes")

    generators = {
        "vegetation_indices": generate_vegetation_indices,
        "climate_indicators": generate_climate_indicators,
        "soil_properties": generate_soil_properties,
        "water_resources": generate_water_resources,
        "land_degradation": generate_land_degradation,
        "crop_calendar": generate_crop_calendar,
    }
    for dataset_id, generator in generators.items():
        rows = generator(communes)
        _write_csv_and_parquet(dataset_id, rows)


if __name__ == "__main__":
    main()
