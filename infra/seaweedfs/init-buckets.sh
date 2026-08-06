#!/bin/sh
# One-shot: create the four buckets and set CORS on the publicly-readable ones.
# Anonymous read on assets/serving is granted via s3.json (identity config), not here.
set -eu

ENDPOINT="http://seaweedfs:8333"
BUCKETS="warehouse raw assets serving"

echo "Waiting for S3 gateway at ${ENDPOINT}..."
for i in $(seq 1 30); do
  if aws --endpoint-url "$ENDPOINT" s3 ls >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

for b in $BUCKETS; do
  echo "Creating bucket: $b"
  aws --endpoint-url "$ENDPOINT" s3 mb "s3://$b" || echo "  (already exists)"
done

CORS_CONFIG='{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}'

for b in assets serving; do
  echo "Setting CORS on: $b"
  echo "$CORS_CONFIG" > /tmp/cors.json
  aws --endpoint-url "$ENDPOINT" s3api put-bucket-cors --bucket "$b" --cors-configuration file:///tmp/cors.json
done

echo "Buckets ready:"
aws --endpoint-url "$ENDPOINT" s3 ls
