# MASTER PROMPT — Multi-Source Geospatial Data Platform (POC)

> Paste this file into Claude Code as the project brief, or save it as `docs/MASTER_PROMPT.md` and point Claude Code at it with: *"Read docs/MASTER_PROMPT.md and build the system following the milestone order. Stop at each STOP GATE and report."*

---

## 1. Role and mission

You are building a **proof-of-concept multi-source geospatial data platform**: a lakehouse back end plus two complementary front ends, running entirely from `docker compose up` on a single machine.

The POC must demonstrate five things and nothing more:

1. **Heterogeneous ingestion under one framework** — three source types, three pipelines, one declarative manifest contract.
2. **A real lakehouse** — Apache Iceberg tables on S3-compatible object storage, ACID commits, queryable by SQL and Python.
3. **First-class geospatial** — a raster served as tiles from a STAC catalog, a vector layer on a map, both discoverable in one place.
4. **Self-service analysis for a non-expert** — someone who does not write SQL finds a dataset, filters it, sees a chart and a map, and shares a link.
5. **A catalogue map explorer** — TerriaMap, with its catalog generated automatically from the platform's own STAC catalog, and region mapping working against the platform's administrative boundaries.

This is explicitly **not** production: no HA, no scale, no hardened auth, no backup strategy. Put that sentence in the README.

---

## 2. Non-negotiable constraints

Read these before writing any code. They override any default you would otherwise reach for.

1. **Object storage is SeaweedFS, not MinIO.** Every S3 interaction goes through the SeaweedFS S3 gateway. See §10 — this is the highest-risk part of the build.
2. **Everything runs under one `docker compose.yml`.** No Kubernetes, no external cloud services required to boot.
3. **`make bootstrap` must work on a clean machine.** From `git clone` to a queryable dataset and two loading front ends, one command, no manual steps. This is a gate on every milestone, not a final polish task.
4. **No POC-only shortcuts in the data layer.** Shortcuts in *compute* and *search* are deliberate and reversible. Shortcuts in storage layout, table format, manifests, or metadata are forbidden — they become migrations later.
5. **The system must boot and demo with zero external credentials.** Ship synthetic seed data. Real API and Earth Engine connectors are built but gated behind credentials, with recorded fixtures so the pipelines are testable offline. If GEE credentials are absent, the GEE pipeline runs against a fixture and says so in the UI.
6. **The TerriaMap catalog is generated, never hand-written.** It is produced from the STAC API and the published PMTiles registry by a Dagster asset, so publishing a new dataset updates the map portal with no manual edit. Hand-authored catalog JSON is a build failure.
7. **Verify, don't assume, every container image tag and every third-party config key.** Several of these projects changed registries and config schemas recently. When unsure, check the project's own docs or `docker run --rm <image> --help` before writing config. Never invent an environment variable name.
8. **Do not add services beyond the list in §4.** If you believe one is needed, stop and ask.

---

## 3. Architecture summary

Storage substrate is SeaweedFS's S3 API. Format follows modality: **Iceberg + Parquet/GeoParquet** for tabular and vector, **COG + STAC** for raster, **PMTiles** for pre-rendered vector tiles. Three catalogs, separate jobs: **Lakekeeper** (Iceberg REST catalog), **pgstac/stac-fastapi** (spatiotemporal discovery across all modalities), and a Postgres table for run/lineage records. **Cube Core** is the semantic layer that turns physical tables into plain-language metrics.

```
Sources → Dagster connectors → SeaweedFS (raw / warehouse / assets / serving)
                                 │
      ┌──────────────────────────┼──────────────────────────┐
      │                          │                          │
 Iceberg tables            COG + STAC                   PMTiles
      │                          │                          │
     Cube                  stac-api / TiTiler              │
      │                          │                          │
      ├──────────→ BFF ──→ Portal (3 screens)  ←────────────┤
      │                          │                          │
      └──────────────────→ Terria catalog asset ────────────┘
                                 │
                            TerriaMap
```

---

## 4. Service inventory

Exactly these. Nothing more.

| Service | Image / build | Purpose | Port |
|---|---|---|---|
| `seaweedfs` | `chrislusf/seaweedfs` | master + volume + filer + S3 gateway (all-in-one) | 8333 (S3), 9333, 8888 |
| `seaweedfs-init` | `amazon/aws-cli` or `minio/mc` | one-shot: create buckets, set anonymous read on public buckets | — |
| `postgres` | `postgis/postgis:16-3.4` | databases: `pgstac`, `dagster`, `cube`, `platform` | 5432 |
| `pgstac-init` | `ghcr.io/stac-utils/pgstac` | one-shot: `pypgstac migrate` | — |
| `lakekeeper` | Lakekeeper catalog image — **verify coordinates** | Iceberg REST catalog | 8181 |
| `lakekeeper-init` | `curlimages/curl` | one-shot: bootstrap + create warehouse pointing at SeaweedFS | — |
| `dagster` | build `./orchestration` | webserver + daemon, dev mode, single container | 3000 |
| `stac-api` | `ghcr.io/stac-utils/stac-fastapi-pgstac` | STAC API with transactions extension | 8081 |
| `titiler` | `ghcr.io/developmentseed/titiler` | dynamic COG tiles | 8082 |
| `cube` | `cubejs/cube` | semantic layer, DuckDB driver | 4000 |
| `api` | build `./apps/api` | FastAPI BFF: search, dataset metadata, lineage, exports | 8000 |
| `portal` | build `./apps/portal` | React + Vite, three screens, served by nginx | 8080 |
| `terriamap` | build `./apps/terriamap` | catalogue map explorer + CORS proxy (**terriajs-server, not nginx**) | 3001 |
| `keycloak` | `quay.io/keycloak/keycloak` | single dev realm, OIDC | 8083 |
| `jupyter` | build `./infra/jupyter` | notebook with the platform SDK | 8888 |

**Deliberately excluded:** Trino, Spark, Kafka, Flink, ClickHouse, OpenSearch, Martin, OpenMetadata, Marquez. DuckDB replaces Trino; Postgres full-text replaces OpenSearch; a `platform.pipeline_runs` table replaces the lineage services.

---

## 5. Two front ends — division of labour

They are complementary, not redundant. Do not duplicate functionality between them.

| | **Portal** (`apps/portal`) | **TerriaMap** (`apps/terriamap`) |
|---|---|---|
| Purpose | Find, understand and **analyse** data | Browse and **overlay** published map layers |
| Backed by | Cube semantic layer + BFF | STAC catalog + PMTiles + TiTiler |
| User question | *"What is the employment rate by region over time?"* | *"What do these four layers look like together?"* |
| Core screens | Discovery, Dataset page, Workbench | Catalog tree, map, region mapping |
| Built by you | Yes — React + Vite | No — configured only; catalog auto-generated |
| Analysis | Query building, chart/table/map, exports | Layer overlay, time slider, CSV region mapping |

**Cross-links are required in both directions.** A dataset page in the Portal has an "Open in Map" button that deep-links into TerriaMap with that layer enabled. A layer in TerriaMap carries a description link back to its Portal dataset page. This is what makes them feel like one platform rather than two apps sharing a machine.

---

## 6. Repository layout

Create exactly this. It matches the eventual production layout so nothing is thrown away.

```
.
├── docker-compose.yml
├── Makefile
├── .env.example
├── README.md
├── infra/
│   ├── seaweedfs/            s3.json (identities), filer.toml
│   ├── postgres/             init-multiple-db.sh
│   ├── keycloak/             realm.json
│   └── jupyter/              Dockerfile
├── orchestration/            Dagster
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── platform_orchestration/
│       ├── definitions.py
│       ├── resources/        seaweedfs, iceberg, stac, duckdb
│       ├── assets/           per-dataset assets, partitioned
│       │   └── terria_catalog.py   ← generates the TerriaMap catalog
│       ├── sensors/
│       └── ops/              registered preprocessing op library
├── connectors/
│   ├── base/                 manifest schema, contract, run-record emitter
│   ├── api_source/           dlt-based
│   ├── file_source/          GDAL/OGR
│   ├── gee_source/           recipe interpreter (§8.2)
│   └── web_source/           stretch goal
├── recipes/
│   ├── datasets/             *.yaml ingestion manifests
│   └── gee/                  *.yaml GEE recipes
├── semantic/                 Cube model: cubes/, views/
├── quality/                  Soda checks
├── sample-data/              synthetic seed data + GEE fixtures
├── apps/
│   ├── api/                  FastAPI BFF
│   ├── portal/               React + Vite front end
│   └── terriamap/            Dockerfile + config overrides + region map assets
├── notebooks/
├── sdk/                      thin Python client
├── tests/
└── docs/
    ├── DEMO_SCRIPT.md
    ├── RUNBOOK.md
    └── adr/                  one ADR per real decision
```

---

## 7. Build order — milestones and STOP GATES

Work milestone by milestone. **At each STOP GATE: run the verification, report the result with command output, and wait for confirmation before continuing.** Do not batch milestones.

### M1 — Object storage and compose skeleton

- `docker-compose.yml` with `seaweedfs`, `seaweedfs-init`, `postgres` only.
- SeaweedFS all-in-one with S3 gateway, identity config, persistent volume. See §10.
- Four buckets: `warehouse`, `raw`, `assets`, `serving`. `assets` and `serving` readable anonymously.
- Postgres with four databases via an init script.
- Healthchecks on both; `depends_on: condition: service_healthy` used everywhere from here on.
- `Makefile` with `bootstrap`, `up`, `down`, `logs`, `reset`, `test`.
- **`tests/test_seaweedfs_compat.py`** — the compatibility suite in §10.4. Write it now, not later.

**STOP GATE 1 —** verify:
```bash
make reset && make bootstrap
aws --endpoint-url http://localhost:8333 s3 ls           # four buckets
aws --endpoint-url http://localhost:8333 s3 cp README.md s3://raw/test.md
curl -f -r 0-99 http://localhost:8333/serving/test.md    # range request works
docker compose exec postgres psql -U $PG_USER -l         # four databases
make test                                                 # compat suite green
```

### M2 — Iceberg catalog and first table

- Add `lakekeeper` + `lakekeeper-init`. Bootstrap the catalog, create a warehouse whose storage profile points at `s3://warehouse` on SeaweedFS with **path-style addressing** (§10.3).
- Add `dagster`. One hello-world asset that writes an Iceberg table with PyIceberg.
- Add `jupyter` with DuckDB + `httpfs` + `spatial` + `iceberg` extensions preconfigured against SeaweedFS.

**STOP GATE 2 —** a Dagster run creates `bronze.hello`, files are visible under `s3://warehouse/`, and a notebook reads the table back with DuckDB. Report the exact `SET s3_*` settings that worked.

### M3 — Ingestion framework and two datasets

- **The manifest contract** (§8.1) — schema, loader, validator, and a shared `PipelineRun` record written to `platform.pipeline_runs`.
- **Every pipeline run must produce all five outputs**: raw artifact with checksum, normalised asset, catalog registration, run/lineage record, quality report. A run producing fewer is a failed run — enforce this in the framework, not by convention.
- **Dataset A (tabular)**: `api_source` connector using `dlt`, with a synthetic generator in `sample-data/` so it works with no credentials.
- **Dataset B (boundaries)**: `file_source` connector, GDAL/OGR → GeoParquet → Iceberg. **Hard-fail if CRS is undeclared.** Geometry uses the V2 bridge pattern: WKB `binary` column + explicit `bbox_minx/miny/maxx/maxy` columns + CRS in table properties. Do not use Iceberg v3 native geo types in the POC.
- `tippecanoe` in the Dagster image → PMTiles → `s3://serving/pmtiles/`.
- A **published-layers registry** table in `platform` recording every PMTiles layer with its bounds, min/max zoom, ID property and source dataset. The Terria catalog generator reads this in M7.
- Soda Core checks as Dagster asset checks.

**STOP GATE 3 —** both datasets materialise; `platform.pipeline_runs` has complete records; PMTiles is fetchable with range requests; quality checks visibly pass and visibly fail when fed bad data.

### M4 — Raster, STAC and the GEE recipe

- `stac-api` + `pgstac-init` + `titiler`.
- **Dataset C (raster)**: `gee_source` connector implementing the recipe schema (§8.2).
  - Recipe interpreter over a **registered `op` library** — each `op` declares whether it is period-decomposable.
  - **Validator** rejecting a recipe whose `incremental_strategy` is invalid for its `reduction.window` (§8.2).
  - **Contributing-asset manifest** and set-difference change detection: store the exact source asset IDs per published period; refresh compares hashes, not dates.
  - **Path B only** (direct pull via `xee`/`computePixels` → COG → SeaweedFS). No GCS staging bucket.
  - Without EE credentials, run against `sample-data/gee_fixtures/`, set `provenance.mode = "fixture"`, and surface that in both front ends.
- STAC items carry `processing:` extension fields plus the contributing-asset manifest.
- Zonal statistics: Dataset C × Dataset B → `gold` Iceberg table.

**STOP GATE 4 —** a COG renders as XYZ tiles in a browser; the STAC API returns the item with provenance; forcing a late-arriving asset into the fixture causes **exactly one** period to reprocess. Demonstrate that last point explicitly.

### M5 — Semantic layer and BFF

- `cube` with a model over the gold tables. Every measure and dimension carries `title`, `description` and, where relevant, `meta.caveat`. **CI fails on a measure without a description.**
- `meta.geo_join` convention on region dimensions pointing at Dataset B.
- `api` (FastAPI BFF): `GET /search`, `GET /datasets/{id}`, `GET /datasets/{id}/lineage`, `GET /datasets/{id}/preview`, `POST /export`, and `GET /datasets/{id}/terria-link` returning a TerriaMap deep link.
- `keycloak` with one dev realm; OIDC on the BFF; token forwarded to Cube as the security context.

**STOP GATE 5 —** `curl` against the BFF returns a governed metric with its caveat text; search returns sensible results for five plain-language terms.

### M6 — Portal front end

Three screens, described in §9. React + Vite + MapLibre GL JS + Observable Plot (or Vega-Lite) + Cube JS client + TanStack Query. Nginx-served production build.

**STOP GATE 6 —** a person who has not seen the system finds a dataset, opens the workbench, produces a choropleth, and shares a URL that reproduces the exact state in another browser.

### M7 — TerriaMap

This milestone has three distinct parts; treat them as three sub-gates.

**M7a — Container and serving.** Build TerriaMap from the upstream starter repo in a multi-stage Dockerfile. **Run `terriajs-server`, not a bare nginx** — Terria needs its CORS proxy for third-party services and for anything not served with permissive headers. Expect a long `npm` build; cache aggressively and pin the Terria version in an ADR. Configure `wwwroot/config.json` with `initializationUrls` pointing at the generated catalog.

**M7b — Generated catalog.** A Dagster asset `terria_catalog` that reads:
- the **STAC API** — every collection and item becomes a catalog member,
- the **published-layers registry** from M3 — every PMTiles layer becomes a vector tile member,
- the **manifest metadata** — title, description, license, caveats become the member's `description` and `info` sections, with a link back to the Portal dataset page.

It writes `catalog.json` to `s3://serving/terria/catalog.json`, and TerriaMap loads it from there. **The asset re-materialises whenever any dataset publishes**, so the map portal is never stale. Group members into a small hierarchy (Boundaries / Indicators / Earth observation).

Raster members point at TiTiler (verify whether Terria's COG support or a TiTiler XYZ/WMTS endpoint is the better fit for your Terria version — check the docs, don't guess). Vector members point at the PMTiles URL on `s3://serving/`.

**M7c — Region mapping.** This is the feature that matters most to non-experts and the fiddliest to configure, so budget for it. Terria ships with default region providers that will not include your boundaries. You must register a **custom region provider**:
- vector tiles of Dataset B with a stable ID property per feature,
- a `regionIds` JSON listing the ID values in tile order,
- an entry in `regionMapping.json` describing the provider, its aliases (the column names a user's CSV might use), and the server URL.

Generate all three from Dataset B in the same Dagster asset — never by hand. Include at least two aliases (code and name) so a user's CSV joins whether they used codes or labels.

**STOP GATE 7 —** three checks:
1. TerriaMap loads with a populated catalog tree; enabling a raster layer and a boundary layer together renders both.
2. Publishing a new dataset in Dagster causes it to appear in the TerriaMap catalog after a refresh, with **no file edited by hand**.
3. A user drags a CSV with region codes onto TerriaMap and gets a choropleth, with no GIS knowledge required.

### M8 — Polish and demo

- `sample-data` seeding wired into `make bootstrap`.
- Cross-links working in both directions (§5).
- `docs/DEMO_SCRIPT.md`, `docs/RUNBOOK.md`, ADRs for every real decision.
- Full clean-machine `make reset && make bootstrap`, timed and documented.
- Optional, in this order if time remains: DuckDB-WASM client-side filtering in the Portal workbench; the `web_source` connector with WARC archiving, geocoding and confidence fields.

---

## 8. Data contracts

### 8.1 Ingestion manifest

```yaml
id: employment_indicators
title: "Employment indicators by commune"
description: >
  One sentence a non-specialist understands, plus what the data must not be used for.
source:
  type: api_source            # api_source | file_source | gee_source | web_source
  endpoint: ...
  auth: none | keycloak_client:<id> | env:<VAR>
extract:
  mode: full | incremental
  cursor: <field>
  schedule: "0 3 * * *"
target:
  modality: tabular | vector | raster
  format: iceberg | geoparquet | cog
  zone: bronze/<domain>/<name>
publish:                       # drives the Terria catalog generator
  pmtiles: true | false
  stac_collection: <id or null>
  terria_group: "Boundaries" | "Indicators" | "Earth observation"
  region_provider: <id or null>   # set on boundary datasets only
quality:
  checks: [schema_conformance, no_nulls:<cols>, crs_declared, value_range]
governance:
  owner: <team>
  classification: public | internal | restricted
  source_class: official | derived | modelled | scraped
  license: <spdx>
  citation: <string>
  caveats: <string>
```

Required fields are enforced by the loader. A manifest missing `description`, `caveats`, `owner`, `license` or `source_class` fails validation — this is what keeps the trust badges and the Terria layer descriptions honest.

### 8.2 GEE recipe

Same envelope, plus:

```yaml
sources:
  - collection: <EE collection id>
    collection_version_pin: <hash or as_of date>
    bands: [...]
domain:
  aoi: <asset ref or geojson path>
  crs: EPSG:xxxxx
  scale_m: <int>
  grid_align_to: <collection id>       # pin crsTransform; prevents grid drift between runs
temporal:
  grain: day | month | year
  reduction:
    type: mean | max | percentile | trend | ...
    window: period | rolling | cumulative | whole_series | baseline_relative
steps:                                  # ordered, each `op` registered and tested
  - {id: cloud_mask, op: s2_cloud_shadow_mask, params: {...}}
  - {id: ndvi, op: normalized_difference, params: {nir: B8, red: B4}}
  - {id: composite, op: temporal_reduce, params: {reducer: percentile, p: 90}}
refresh:
  cadence: "0 3 * * *"
  incremental_strategy: append_period   # VALIDATED against temporal.reduction.window
  finality_lag_days: 30
  revision_policy: reprocess_period
  source_version_change: halt_and_notify
```

**Validator matrix — enforce exactly this:**

| `reduction.window` | Allowed `incremental_strategy` |
|---|---|
| `period` | `append_period` |
| `rolling` | `recompute_window` (window ≥ rolling length) |
| `cumulative` | `stateful_merge` |
| `baseline_relative` | `split_baseline` |
| `whole_series` | `full_recompute` |

Also reject: `append_period` where any step's `op` declares cross-period state; any classification step whose model artifact is not pinned by hash.

---

## 9. Portal specification

Three screens. Build no fourth — put further ideas in `docs/backlog.md`.

**Screen 1 — Discovery.** Search over title/description/tags, facets (theme, source type, spatial vs tabular), result cards with trust badges: source class, freshness (green/amber/red against expected cadence), quality pass rate, confidence indicator for scraped or geocoded data. **A dataset with `source_class: scraped`, or a GEE dataset in fixture mode, must never render without its indicator.**

**Screen 2 — Dataset page.** Plain-language description; known limitations; trust badges; live preview (first 100 rows, or a map, or a COG thumbnail via TiTiler); coverage (footprint map + temporal extent); lineage box from `platform.pipeline_runs`; for GEE datasets a **plain-language provenance sentence** generated from the recipe — *"90th-percentile NDVI from 14 cloud-masked scenes, computed under recipe v3 on 2 July 2026"* — with full JSON one click away; buttons for Download, Copy API call, Open in Workbench, **Open in Map** (TerriaMap deep link), Open in Notebook.

**Screen 3 — Workbench.** Left: dimension and measure picker from Cube's `/meta`, plain-language titles with descriptions on hover. Top: filters and time grain. Right: **one query, three views — table, chart, map**. Automatic choropleth when a dimension carries `meta.geo_join`, quantile classification, colourblind-safe palette. Plain-language summary of the current query above the result. **The entire state is encoded in the URL.** Exports and a read-only "Show SQL".

Skip entirely: dashboards, saved queries, user preferences, admin UI, dark mode, i18n.

---

## 10. SeaweedFS — the critical section

This is where the build will go wrong if you are careless. SeaweedFS is S3-compatible but not S3-identical.

### 10.1 Topology

For the POC, run all-in-one:

```
weed server -dir=/data -master.volumeSizeLimitMB=1024 \
  -filer -s3 -s3.config=/etc/seaweedfs/s3.json -s3.port=8333
```

This starts master (9333), volume (8080), filer (8888) and the S3 gateway (8333) in one container. The filer is **required** for the S3 API — S3 buckets are filer directories. Persist `/data` to a named volume.

Healthcheck against the master's cluster status endpoint, not port 8333 alone: the S3 gateway accepts connections before the filer is ready.

### 10.2 Identities and anonymous read

`infra/seaweedfs/s3.json` holds a named platform identity with `Admin`/`Read`/`Write`/`List`/`Tagging`, plus an `anonymous` identity limited to `Read` on `assets` and `serving`. That anonymous identity is what lets TiTiler, PMTiles, the Terria catalog and the browser fetch objects without credentials.

Create buckets in `seaweedfs-init` with the AWS CLI or `mc` against the S3 endpoint, or `weed shell -c "s3.bucket.create -name warehouse"`.

**Set CORS on the `serving` and `assets` buckets.** TerriaMap and the Portal both fetch PMTiles and the catalog directly from the browser; without CORS headers they fail with errors that look like missing files.

### 10.3 Path-style addressing everywhere

SeaweedFS does not do virtual-host-style bucket addressing. **Every client must be told to use path style.**

| Client | Setting |
|---|---|
| **GDAL / TiTiler** | `AWS_S3_ENDPOINT=seaweedfs:8333`, `AWS_HTTPS=NO`, `AWS_VIRTUAL_HOSTING=FALSE`, `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`, `CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,.tiff,.json` |
| **boto3 / AWS CLI** | `endpoint_url=http://seaweedfs:8333`, `config=Config(s3={'addressing_style':'path'})` |
| **DuckDB httpfs** | `SET s3_endpoint='seaweedfs:8333'; SET s3_use_ssl=false; SET s3_url_style='path'; SET s3_region='us-east-1';` |
| **PyIceberg / PyArrow** | FileIO with `s3.endpoint`, `s3.access-key-id`, `s3.secret-access-key`; verify PyArrow's `S3FileSystem` gets `endpoint_override` and virtual addressing disabled |
| **Lakekeeper warehouse** | S3 storage profile with endpoint override and path-style access — **check current config key names against Lakekeeper's docs; do not guess** |
| **Browser (Terria/Portal)** | Public URLs must be `http://<host>:8333/serving/...` path style, and reachable from the browser, not only from inside the compose network |

Region must be set to something (`us-east-1`) even though SeaweedFS ignores it; several clients refuse to sign without one.

### 10.4 Behaviours to verify in M1, not later

`tests/test_seaweedfs_compat.py` asserts each of these:

- multipart upload of a >100 MB object, then download and checksum
- **HTTP range requests** (`Range: bytes=0-1023`) — COG and PMTiles are unusable without this
- `ListObjectsV2` with prefix and delimiter, including pagination beyond 1000 keys
- object overwrite and immediate read-after-write consistency
- delete, and delete of a non-existent key
- anonymous GET on `serving`, and anonymous GET refused on `warehouse`
- CORS preflight on `serving`
- conditional request headers, if Lakekeeper's storage profile relies on them

If any fails, report it and stop — do not work around it silently. Iceberg commit atomicity here lives in Lakekeeper's Postgres metadata rather than in object-store conditional writes, so a gap there is survivable; a gap in range requests is not.

### 10.5 Filer store

Default LevelDB is fine for the POC. If the filer becomes a bottleneck, or you want metadata to survive a volume reset independently, configure `filer.toml` against the existing Postgres. Record the choice in an ADR either way.

---

## 11. Known pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Blank or grey tiles from TiTiler | GDAL S3 env vars wrong | The four variables in §10.3. Budget half a day |
| `docker compose up` fails differently each run | Missing healthchecks / start ordering | `depends_on: condition: service_healthy` everywhere |
| Bucket "not found" despite existing | Virtual-host addressing | Path style, §10.3 |
| Iceberg writes succeed but reads return nothing | Warehouse location mismatch between Lakekeeper and writer | Log the resolved table location on every write |
| PMTiles won't load in the browser | Range requests or CORS | Verify §10.4; set CORS on `serving` |
| TerriaMap shows an empty catalog | `initializationUrls` unreachable from the **browser**, not from the container | Use a host-reachable URL; test with the compose network down |
| Terria fails to load a layer with a CORS error | Terria's proxy not in use | Run `terriajs-server`, not nginx; route through `/proxy/` |
| Region mapping produces a blank map | Region provider not registered, or CSV column name not in aliases | §M7c — generate `regionIds` and `regionMapping.json`; include code *and* name aliases |
| TerriaMap image build takes forever | Full `npm` + gulp build | Multi-stage Dockerfile, aggressive layer caching, pin the version |
| Choropleth doesn't render in the Portal | `meta.geo_join` missing or region codes mismatched | Normalise codes in the gold layer, never in the front end |
| GEE pipeline unrunnable in CI | Credentials assumed present | Fixture mode, §2.5 |
| Grid drift between GEE runs | `scale` used instead of `crsTransform` | Pin `grid_align_to` |

---

## 12. Engineering standards

- **Python**: 3.12, `uv` or `pip-tools` for locking, `ruff` for lint and format, `mypy` on `connectors/` and `orchestration/ops/`. Type hints on all public functions.
- **TypeScript**: strict mode, `eslint` + `prettier`, no `any` in application code.
- **Tests**: `pytest` for connectors, ops, the manifest validator, the recipe validator and the Terria catalog generator. The recipe validator matrix in §8.2 gets exhaustive tests — every window/strategy pair, valid and invalid. The catalog generator gets a golden-file test. Playwright smoke tests for both front ends walking the demo path.
- **Config**: everything through `.env`, with `.env.example` committed and no secrets in Git. Fail fast with a clear message on a missing variable.
- **Commits**: conventional commits, one milestone per branch.
- **Logging**: structured JSON from Dagster and the BFF; every pipeline run logs its run id.
- **ADRs**: `docs/adr/NNNN-title.md` for every real decision — the SeaweedFS filer store, the geometry bridge pattern, DuckDB instead of Trino, the pinned Terria version, any compatibility gap found in §10.4.

---

## 13. Definition of done

1. `git clone && make bootstrap` on a clean machine yields a working system with no manual steps and no external credentials.
2. Three datasets (tabular, vector, raster) materialise from Dagster runs, each with a complete `pipeline_runs` record, passing quality checks, registered in Iceberg and/or STAC.
3. A GEE recipe refresh, given a forced late-arriving asset, reprocesses exactly one period.
4. The recipe validator rejects every invalid window/strategy pair in §8.2, with tests proving it.
5. All three Portal screens work; the workbench produces a choropleth and a shareable URL that reproduces state.
6. TerriaMap loads a **generated** catalog; publishing a dataset updates it with no hand edits; CSV region mapping produces a choropleth.
7. Cross-links work in both directions between Portal and TerriaMap.
8. Trust badges render correctly; scraped and fixture-derived data are visibly labelled.
9. `docs/DEMO_SCRIPT.md` runs start to finish without a restart.
10. `make test` passes.
11. The README states plainly what the POC does not prove.

---

## 14. How to work with me

- **Stop at every STOP GATE.** Report what you verified, paste the command output, and wait.
- **Ask before**: adding any service, changing the storage layout, changing the manifest or recipe schema, hand-writing any Terria catalog content, or working around a SeaweedFS compatibility gap.
- **Decide yourself**: library choices within a milestone, file organisation inside a package, UI component structure, test structure.
- **When a third-party config key or image tag is uncertain**, check the project's documentation or the container's own `--help` first. Say "I verified this against X" or "I could not verify this and here is my assumption" — never present a guess as fact. This applies with particular force to Lakekeeper's storage-profile keys and to TerriaJS catalog member types, both of which have changed across versions.
- **If a milestone turns out to be larger than it looked**, say so at the gate and propose a split rather than silently expanding scope.

Start with M1.
