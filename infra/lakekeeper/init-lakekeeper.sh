#!/bin/sh
# One-shot: bootstrap Lakekeeper (sets the initial admin/project) and create
# the "poc" warehouse pointing at s3://warehouse on SeaweedFS. Idempotent:
# both calls are safe to re-run (a 4xx on an already-done step is swallowed).
set -eu

BASE="http://lakekeeper:8181"

echo "Bootstrapping Lakekeeper..."
BOOTSTRAP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE/management/v1/bootstrap" \
  -H "Content-Type: application/json" \
  -d '{"accept-terms-of-use": true}')
BOOTSTRAP_STATUS=$(echo "$BOOTSTRAP_RESPONSE" | tail -n1)
if [ "$BOOTSTRAP_STATUS" != "204" ] && [ "$BOOTSTRAP_STATUS" != "200" ]; then
  echo "  bootstrap returned HTTP $BOOTSTRAP_STATUS: $(echo "$BOOTSTRAP_RESPONSE" | head -n -1)"
  echo "  (treating as already-bootstrapped and continuing)"
fi

echo "Creating warehouse 'poc'..."
WAREHOUSE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE/management/v1/warehouse" \
  -H "Content-Type: application/json" \
  -d @/scripts/create-default-warehouse.json)
WAREHOUSE_STATUS=$(echo "$WAREHOUSE_RESPONSE" | tail -n1)
if [ "$WAREHOUSE_STATUS" != "201" ] && [ "$WAREHOUSE_STATUS" != "200" ]; then
  echo "  warehouse creation returned HTTP $WAREHOUSE_STATUS: $(echo "$WAREHOUSE_RESPONSE" | head -n -1)"
  echo "  (treating as already-exists and continuing — re-run to see the real error otherwise)"
fi

echo "Lakekeeper ready."
