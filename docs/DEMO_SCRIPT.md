# Demo Script — Multi-Source Geospatial Data Platform POC

Time: ~10 minutes. Audience: technical stakeholders.

## Prerequisites

```bash
make bootstrap   # one-command cold start
```

Wait for "Bootstrap complete" message. All URLs below are localhost.

---

## Act 1 — The Lakehouse (2 min)

**Goal:** Show heterogeneous ingestion under one framework.

1. Open **Dagster** at http://localhost:3000
2. Navigate to the Asset Graph — point out two internal pipelines:
   - `communes_boundaries` (file_source → vector/GeoParquet → PMTiles)
   - `ndvi_composite` (gee_source/fixture → raster/COG → STAC)
3. Materialize all assets (Shift+click to select all, then "Materialize")
4. While running, show a manifest YAML (`recipes/datasets/communes_boundaries.yaml`):
   - Declarative contract: source, quality checks, governance, publish config
   - "One YAML per dataset — the platform reads intent, not implementation"

**Talking point:** Different source types, different storage formats,
one orchestration framework, one contract shape.

---

## Act 2 — Alternative Data Layers (3 min)

**Goal:** Show the platform consuming external open-data WMS layers.

1. Open **TerriaMap** at http://localhost:3001
2. Click **"+ Data"** → four groups appear:
   - Boundaries, Earth Observation, Alternative Data
3. Expand **Alternative Data** — 7 real external layers:
   - NDVI Végétation (MODIS Terra) — health of vegetation
   - Occupation du Sol (ESA WorldCover) — land use at 10 m
   - Précipitations (GPM NASA) — monthly rainfall
   - Température de Surface — thermal stress
   - Humidité du Sol (SMAP) — irrigation and drought
   - Évapotranspiration — crop water balance
   - Feux Actifs (VIIRS) — active fire detection
4. Add **NDVI Végétation** → real MODIS satellite data renders on Morocco
5. Add **Occupation du Sol** → land use/land cover overlay
6. Toggle layers on/off to compare

**Talking point:** These are live WMS feeds from NASA and ESA — real
satellite data, no download needed, no authentication. The platform
integrates external data alongside internal pipeline outputs.

---

## Act 3 — Self-Service Discovery (3 min)

**Goal:** A non-expert finds data, understands it, and analyses it.

1. Open the **Portal** at http://localhost:8080
2. The Discovery page lists datasets with badges (source type, modality)
3. Click into the Communes Boundaries dataset page:
   - Description, limitations (yellow callout), provenance, license
   - Lineage table shows pipeline runs with row counts
4. Click **"Open in Map"** → TerriaMap opens with the layer pre-selected
5. In TerriaMap, expand **Boundaries** → add commune polygons
6. Expand **Earth Observation** → add NDVI zonal statistics
   - Click a commune polygon → Feature Information shows NDVI values
7. Show the description panel → click **"View in Portal"** link

**Talking point:** Two front ends, one platform. Portal for discovery
and analysis, TerriaMap for spatial overlay. Cross-links connect them.

---

## Act 4 — The Pipeline (2 min)

**Goal:** Publishing a new dataset updates TerriaMap automatically.

1. Back in **Dagster**, materialize the `terria_catalog` asset
2. Show the logs: it reads manifests, published layers, STAC collections,
   and injects external WMS layers
3. Refresh TerriaMap — the catalog reflects whatever Dagster produced
4. "No file was edited by hand — the catalog is generated from the
   platform's own metadata plus external data sources"

**Talking point:** The map portal is a view over the data catalog, not a
separate manually-maintained configuration. External alternative data
layers are integrated alongside internal pipeline outputs.

---

## Closing

| What the POC proves | How |
|---|---|
| Heterogeneous ingestion | Multiple source types, 1 manifest contract |
| Alternative data integration | 7 WMS layers from NASA/ESA, zero auth |
| Real lakehouse | Iceberg on SeaweedFS, ACID commits |
| First-class geospatial | Raster tiles + vector overlays, one catalog |
| Self-service discovery | Portal with governance badges and lineage |
| Catalogue map explorer | TerriaMap, auto-generated catalog, region mapping |
