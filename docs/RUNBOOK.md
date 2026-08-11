# Runbook — Multi-Source Geospatial Data Platform POC

This is a POC, not production. No HA, no scale, no hardened auth, no backup
strategy.

## Quick Start

```bash
git clone <repo-url> && cd GeoSpacialData
make bootstrap
```

This builds all images, starts all services, waits for health checks, and
seeds sample data. Takes 3-8 minutes depending on network and CPU.

## Service Map

| Service | URL | Credentials |
|---|---|---|
| Portal | http://localhost:8080 | none (public) |
| TerriaMap | http://localhost:3001 | none (public) |
| Dagster | http://localhost:3000 | none (dev mode) |
| BFF API | http://localhost:8000 | optional Keycloak token |
| STAC API | http://localhost:8081 | none |
| TiTiler | http://localhost:8082 | none |
| Cube | http://localhost:4000 | API secret in `.env` |
| SeaweedFS S3 | http://localhost:8333 | `platform` / `platform-dev-secret-please-rotate` |
| SeaweedFS Filer | http://localhost:8888 | none |
| Keycloak | http://localhost:8083 | admin: `admin`/`admin`, user: `demo`/`demo` |
| Postgres | localhost:5432 | `platform` / `platform-dev-secret-please-rotate` |
| Lakekeeper | http://localhost:8181 | none |
| Jupyter | http://localhost:8890 | token-free (dev config) |

## Common Operations

### Start / Stop / Reset

```bash
make up        # start all services (builds if needed)
make down      # stop all services (preserves data volumes)
make reset     # stop all + delete volumes (clean slate)
make bootstrap # full cold start with seed data
make seed      # re-seed sample data (services must be running)
make test      # run SeaweedFS compatibility suite
```

### Materialize All Dagster Assets

Open http://localhost:3000, go to the Asset Graph, select all assets, click
"Materialize". Or use the GraphQL API:

```bash
curl -X POST http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { launchRun(executionParams: { selector: { repositoryLocationName: \"platform_orchestration.definitions\", repositoryName: \"__repository__\", jobName: \"__ASSET_JOB\" }, runConfigData: \"{}\" }) { __typename ... on LaunchRunSuccess { run { runId } } } }"}'
```

### Check Service Health

```bash
docker compose ps
```

All long-running services should show `healthy`. One-shot init services
(`seaweedfs-init`, `lakekeeper-init`, `pgstac-init`, `terria-init`,
`lakekeeper-migrate`) should show `Exited (0)`.

### View Logs

```bash
make logs                          # all services
docker compose logs dagster -f     # single service, follow
docker compose logs terria --tail 50
```

## Troubleshooting

### TerriaMap shows blank map or 3D globe crash

The map is forced to 2D Leaflet mode. If it reverts to 3D (e.g., after
clearing localStorage), reload the page — `viewerMode: "2d"` in the init
file will re-apply.

### Dagster asset fails with AccessDenied on S3 PUT

Known SeaweedFS all-in-one quirk (see ADR 0003). Check
`docker compose logs seaweedfs` for "Lost lock s3.leader" messages. Retry
the materialization — it almost always succeeds on the second attempt.

### Container exits immediately

```bash
docker compose logs <service-name>   # check the error
docker compose up -d <service-name>  # restart it
```

Common causes: a dependency service isn't healthy yet (check `depends_on`
conditions), or a one-shot init job failed (check its exit code).

### Port conflict

If a port is already in use, either stop the conflicting process or change
the host port in `docker-compose.yml` (the left side of the `ports:` mapping).

### Rebuilding a single service

```bash
docker compose up -d --build <service-name>
```

## Architecture Decisions

See `docs/adr/` for recorded decisions:

- 0001: SeaweedFS all-in-one mode and identity config
- 0002: Lakekeeper config, image tag, and missing database
- 0003: SeaweedFS conditional PUT flakiness
- 0004: TerriaJS GeoJSON over PMTiles
- 0005: TerriaMap forced to 2D Leaflet mode
- 0006: TerriaMap catalog via shared Docker volume

## Data Flow

```
sample-data/ ──→ Dagster connectors ──→ SeaweedFS (raw → bronze → gold → serving)
                                              │
                  ┌───────────────────────────┤
                  │                           │
             Iceberg tables              GeoJSON / CSV / COG
                  │                           │
                 Cube                    TerriaMap catalog
                  │                           │
                 BFF ──→ Portal          TerriaMap
```

## Volumes

| Volume | Purpose |
|---|---|
| `seaweedfs_data` | All object storage data (S3 buckets) |
| `postgres_data` | All databases (pgstac, dagster, cube, platform, lakekeeper) |
| `terria_init` | Shared init files between Dagster and TerriaMap |

`make reset` deletes all three volumes for a clean slate.
