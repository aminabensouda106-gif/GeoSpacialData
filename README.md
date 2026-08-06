# Multi-Source Geospatial Data Platform — POC

A proof-of-concept multi-source geospatial data platform: a lakehouse back end
plus two complementary front ends (a data-analysis Portal and a TerriaMap
catalogue map explorer), running entirely from `docker compose up` on a
single machine.

Full spec: [`documentation/MASTER_PROMPT_GEOPLATFORM_POC_v2.md`](documentation/MASTER_PROMPT_GEOPLATFORM_POC_v2.md).
Design rationale / prior art: [`documentation/multi_source_geospatial_lakehouse_architecture_1.md`](documentation/multi_source_geospatial_lakehouse_architecture_1.md).

## What this POC demonstrates

1. Heterogeneous ingestion (API, file, satellite/GEE) under one manifest contract.
2. A real lakehouse — Apache Iceberg tables on S3-compatible object storage.
3. First-class geospatial — raster tiles from a STAC catalog, vector layers on a map.
4. Self-service analysis for a non-expert (Portal: find → filter → chart/map → share).
5. A catalogue map explorer (TerriaMap) with a **generated** catalog — never hand-written.

## What this POC does not prove

This is explicitly **not** production: no high availability, no scale testing, no
hardened auth beyond a single Keycloak dev realm, no backup/DR strategy. Storage,
table-format and manifest decisions were made to be migration-safe; everything
else (compute engine choice, search, UI polish) took deliberate POC shortcuts —
see `docs/adr/` for what was cut and why.

## Status

Being built milestone-by-milestone per the master prompt (M1–M8). Current state
is tracked in this README as milestones land; see `docs/RUNBOOK.md` (added at M8)
for the full operational picture and `docs/DEMO_SCRIPT.md` for the guided walkthrough.

- [x] M1 — Object storage (SeaweedFS) + Postgres compose skeleton
- [x] M2 — Iceberg catalog (Lakekeeper) + Dagster + Jupyter
- [x] M3 — Ingestion framework, tabular + boundary datasets
- [ ] M4 — Raster, STAC, GEE recipe pipeline
- [ ] M5 — Semantic layer (Cube) + BFF
- [ ] M6 — Portal front end
- [ ] M7 — TerriaMap (generated catalog + region mapping)
- [ ] M8 — Cross-links, demo script, polish

## Quick start

```bash
cp .env.example .env      # defaults work as-is; edit only for real credentials
make bootstrap             # or: bash scripts/bootstrap.sh (no GNU make needed)
make test                  # or: bash scripts/test.sh
```

Requires Docker Desktop (or Docker Engine + Compose v2) running locally. No
external API credentials are required to boot — real connectors (e.g. Google
Earth Engine) fall back to recorded fixtures when credentials are absent, and
say so in the UI.

## Repository layout

See `documentation/MASTER_PROMPT_GEOPLATFORM_POC_v2.md` §6 for the full,
intended layout. Directories are created as the milestone that needs them lands.

## Engineering notes worth knowing up front

- **Object storage is SeaweedFS, not MinIO** — S3-compatible but not
  S3-identical; see `tests/test_seaweedfs_compat.py` and `docs/adr/` for the
  compatibility gaps found and how they were handled.
- **No `make` / `aws` CLI assumed on the host.** Every `Makefile` target wraps
  a POSIX shell script in `scripts/`; verification commands that need the AWS
  CLI run it from a throwaway container rather than assuming a host install.
- **The TerriaMap catalog is generated, never hand-written** — see the
  `terria_catalog` Dagster asset (added at M7).
