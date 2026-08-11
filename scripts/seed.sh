#!/usr/bin/env bash
# Upload sample data to SeaweedFS serving bucket so TerriaMap and Portal
# have data from first boot.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Seeding sample data ==="

echo "Waiting for Dagster container..."
for i in $(seq 1 60); do
  if docker compose exec -T dagster python -c "print('ok')" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

docker compose exec -T dagster python -c "
import boto3, json, os

s3 = boto3.client('s3',
    endpoint_url=os.environ.get('SEAWEEDFS_ENDPOINT', 'http://seaweedfs:8333'),
    aws_access_key_id=os.environ.get('SEAWEEDFS_ACCESS_KEY', 'platform'),
    aws_secret_access_key=os.environ.get('SEAWEEDFS_SECRET_KEY', 'platform-dev-secret-please-rotate'),
    region_name='us-east-1')

# Upload communes_boundaries.geojson
geojson_path = 'sample-data/communes_boundaries.geojson'
if os.path.exists(geojson_path):
    with open(geojson_path, 'rb') as f:
        s3.put_object(Bucket='serving', Key='geojson/communes_boundaries.geojson',
                      Body=f.read(), ContentType='application/geo+json')
    print('  communes_boundaries.geojson -> serving/geojson/')

print('Seed upload complete.')
"

echo ""
echo "Seed complete. Data is available in TerriaMap and Portal."
echo "For full pipeline runs, open Dagster at http://localhost:3000 and materialize all assets."
