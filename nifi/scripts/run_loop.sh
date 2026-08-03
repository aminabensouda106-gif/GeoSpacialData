#!/bin/sh
set -e

INTERVAL_HOURS="${INTERVAL_HOURS:-24}"

while true; do
  echo "$(date -Iseconds) - lancement export NDVI"
  python gee_export.py || echo "$(date -Iseconds) - echec de l'export, nouvelle tentative au prochain cycle"
  echo "$(date -Iseconds) - prochain export dans ${INTERVAL_HOURS}h"
  sleep "$((INTERVAL_HOURS * 3600))"
done
