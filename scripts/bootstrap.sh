#!/usr/bin/env bash
# `git clone && make bootstrap` must produce a running, queryable system with
# no manual steps (definition of done #1). This script is the one entrypoint
# that does that: bring the stack up, wait for health checks, seed data.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found — copying .env.example (edit it if you have real credentials to add)."
  cp .env.example .env 2>/dev/null || true
fi

bash scripts/up.sh

echo ""
echo "Waiting for one-shot init jobs to complete..."
for job in seaweedfs-init lakekeeper-init pgstac-init terria-init; do
  if docker compose ps "$job" --format '{{.Name}}' 2>/dev/null | grep -q .; then
    echo "  waiting for $job..."
    docker compose wait "$job" 2>/dev/null || true
  fi
done

echo ""
echo "Waiting for services to become healthy..."
for svc in seaweedfs postgres lakekeeper stac-api cube api terria dagster; do
  printf "  %-20s" "$svc"
  for i in $(seq 1 60); do
    health=$(docker compose ps "$svc" --format '{{.Health}}' 2>/dev/null || echo "")
    if [ "$health" = "healthy" ]; then
      echo "healthy"
      break
    fi
    if [ "$i" -eq 60 ]; then
      echo "timeout (may still be starting)"
    fi
    sleep 3
  done
done

echo ""
bash scripts/seed.sh

echo ""
echo "=== docker compose ps ==="
docker compose ps

echo ""
echo "Bootstrap complete."
echo "  Portal:          http://localhost:8080"
echo "  TerriaMap:       http://localhost:3001"
echo "  Dagster:         http://localhost:3000"
echo "  BFF API:         http://localhost:8000"
echo "  STAC API:        http://localhost:8081"
echo "  SeaweedFS S3:    http://localhost:8333"
echo "  Keycloak:        http://localhost:8083  (admin/admin)"
echo ""
echo "Run 'make test' to verify the SeaweedFS compatibility suite."
