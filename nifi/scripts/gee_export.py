"""
Export automatisé du NDVI (Sentinel-2) sur la zone d'étude pilote, vers le dossier de
dépôt surveillé par NiFi (voir docker-compose.yml, service gee-exporter).

Reprend la logique de gee_scripts/vegetation_cover_ndvi.js (masque nuages QA60, NDVI
normalizedDifference B8/B4), mais restreinte à une zone pilote pour rester dans les
limites de taille de ee.Image.getDownloadURL (cf. cahier des charges §16 : "Limiter la
zone d'étude pilote" face au risque de volumétrie).
"""

import argparse
import datetime as dt
import os

import ee
import requests

EE_PROJECT_ID = os.environ["EE_PROJECT_ID"]
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/gee")
CLOUD_FILTER_PCT = 20

# Zone d'étude pilote (sous-ensemble de Maroc + Sahara occidental), ajustable par variables d'env
PILOT_BBOX = [
    float(os.environ.get("PILOT_MIN_LON", -8.2)),
    float(os.environ.get("PILOT_MIN_LAT", 33.2)),
    float(os.environ.get("PILOT_MAX_LON", -6.5)),
    float(os.environ.get("PILOT_MAX_LAT", 34.3)),
]


def mask_s2_clouds(image):
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
    return image.updateMask(mask).divide(10000)


def export_ndvi(start_date: str, end_date: str) -> str:
    ee.Initialize(project=EE_PROJECT_ID)

    roi = ee.Geometry.Rectangle(PILOT_BBOX)

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start_date, end_date)
        .filterBounds(roi)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_FILTER_PCT))
        .map(mask_s2_clouds)
    )

    composite = s2.mean().clip(roi)
    ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")

    url = ndvi.getDownloadURL({"region": roi, "scale": 500, "format": "GEO_TIFF"})

    response = requests.get(url, timeout=300)
    response.raise_for_status()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"ndvi_{start_date}_{end_date}.tif"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(response.content)

    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=int(os.environ.get("LOOKBACK_DAYS", 14)))
    args = parser.parse_args()

    end = dt.date.today()
    start = end - dt.timedelta(days=args.days)
    end_exclusive = end + dt.timedelta(days=1)

    path = export_ndvi(start.isoformat(), end_exclusive.isoformat())
    print(f"NDVI exporte : {path}")


if __name__ == "__main__":
    main()
