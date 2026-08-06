#!/usr/bin/env bash
# `git clone && make bootstrap` must produce a running, queryable system with
# no manual steps (definition of done #1). This script is the one entrypoint
# that does that: bring the stack up, wait for the one-shot init jobs to
# finish, then print a status summary.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found — copying .env.example (edit it if you have real credentials to add)."
  cp .env.example .env
fi

bash scripts/up.sh

echo
echo "Waiting for one-shot init jobs to complete..."
for job in seaweedfs-init; do
  if docker compose ps "$job" >/dev/null 2>&1; then
    docker compose wait "$job" 2>/dev/null || true
  fi
done

echo
echo "=== docker compose ps ==="
docker compose ps

echo
echo "Bootstrap complete."
echo "  SeaweedFS S3:    http://localhost:8333"
echo "  SeaweedFS filer: http://localhost:8888"
echo "  Postgres:        localhost:5432 (db: platform/pgstac/dagster/cube)"
echo
echo "Run 'make test' (or 'bash scripts/test.sh') to verify the SeaweedFS compatibility suite."
