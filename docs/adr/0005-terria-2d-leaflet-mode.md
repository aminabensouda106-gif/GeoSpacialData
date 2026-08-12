# 0005 — TerriaMap forced to 2D Leaflet mode

**Status:** Superseded (see Update below) — originally Accepted (M7)

## Context

TerriaJS defaults to 3D mode using CesiumJS, which requires a valid Cesium
Ion access token for terrain and Bing imagery tiles. Without a token (the
POC runs with zero external credentials per constraint #5), Cesium throws
continuous 404 errors and renders an unusable black globe.

## Decision

Force 2D Leaflet mode via three mechanisms:

1. `"viewerMode": "2d"` in the init file (`geodata.json`) — sets the
   initial viewer mode when loading the catalog.
2. `"map": "2d"` in `config.json` `parameters` — sets the default map mode
   at the application level.
3. `"useCesiumIonTerrain": false` and `"useCesiumIonBingImagery": false` in
   `config.json` `parameters` — disables Cesium Ion requests entirely.

## Consequences

- The 3D globe, terrain draping, and 3D Tiles features are unavailable.
  This is acceptable for the POC's 2D choropleth and overlay use cases.
- If a Cesium Ion token is later provided, removing the `"map": "2d"`
  setting and the `useCesium*: false` flags re-enables 3D mode.

## Update — reversed to 3dSmooth

`"map"`/`"viewerMode"` are now `"3dSmooth"` instead of `"2d"` in both
`config.json` and `geodata.json`, with `"cesiumTerrainUrl": ""` added
alongside the existing `useCesiumIonTerrain: false` /
`useCesiumIonBingImagery: false` flags.

`3dSmooth` runs CesiumJS on a plain WGS84 ellipsoid — no terrain draping,
no Bing imagery, no Cesium Ion requests of any kind — so the zero-external-
credentials constraint from the original decision still holds; only the
default *viewer mode* changes, not the token requirement. The black-globe
failure mode this ADR was written to avoid was specifically terrain/imagery
requests hitting Ion with no token, not 3D rendering itself.

Users can still switch to the flat 2D Leaflet view at any time via
TerriaJS's built-in viewer-mode control in the map UI — this change only
affects the default on load.
