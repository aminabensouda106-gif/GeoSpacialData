# 0004 — TerriaJS: GeoJSON catalog type instead of PMTiles/MVT

**Status:** Accepted (M7)

## Context

The master prompt specifies PMTiles as the serving format for vector layers,
and the Dagster pipeline (M3) produces PMTiles via tippecanoe. However,
TerriaJS v8 does not support `pmtiles` or `mvt` as catalog item types. Its
supported types are: `geojson`, `wms`, `wmts`, `csv`, `czml`, `kml`, `gpx`,
and `3d-tiles`.

## Decision

Use `"type": "geojson"` for vector layers and `"type": "csv"` for tabular
datasets in the Terria catalog. The GeoJSON files are uploaded to the
`serving` bucket alongside the existing PMTiles, and TerriaJS fetches them
through its built-in CORS proxy (`proxy/http://seaweedfs:8333/...`).

The region mapping configuration (`regionMapping.json`) was also changed
from `"serverType": "MVT"` to `"serverType": "GeoJSON"` for the same reason.

## Consequences

- GeoJSON is fine for the POC's ten-commune dataset; it would not scale to
  hundreds of thousands of features. A production system would need either a
  WMS/WMTS tile server in front of PostGIS, or TerriaJS would need to add
  PMTiles support upstream.
- PMTiles are still generated and stored; nothing was removed from the
  pipeline. The serving format for Terria is simply a different path.
