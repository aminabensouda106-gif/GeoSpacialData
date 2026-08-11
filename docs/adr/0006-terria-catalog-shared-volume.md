# 0006 — TerriaMap catalog via shared Docker volume

**Status:** Accepted (M7)

## Context

The master prompt requires that the TerriaMap catalog is generated (never
hand-written) by a Dagster asset, so publishing a new dataset updates the
map with no manual edit. TerriaJS's `terriajs-server` serves init files
from `/app/wwwroot/init/`, and there is no API to push catalog updates at
runtime.

## Decision

Use a named Docker volume (`terria_init`) shared between the `dagster` and
`terria` containers:

1. A one-shot `terria-init` service (busybox) seeds the volume with the
   hand-authored `geodata.json` from `infra/terria/init/` using `cp -n`
   (no-clobber) so it does not overwrite a Dagster-generated version.
2. The `dagster` container mounts the same volume at
   `$TERRIA_INIT_DIR` (`/opt/dagster/app/terria-init`).
3. When the `terria_catalog` asset materializes, it writes `geodata.json`
   to the shared volume. TerriaMap serves the updated file on the next
   browser refresh.

## Consequences

- TerriaMap does not need to restart for catalog updates — a browser
  refresh is enough.
- The seed file provides a working catalog even before any Dagster pipeline
  runs, so TerriaMap is usable immediately after `make bootstrap`.
- The `cp -n` flag means the seed only applies to a fresh volume; once
  Dagster has written its version, the seed is ignored.
