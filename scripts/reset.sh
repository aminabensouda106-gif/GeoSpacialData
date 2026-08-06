#!/usr/bin/env bash
# Tears down the stack AND deletes its volumes — used to prove a clean-machine
# bootstrap (§13 point 1 of the master prompt). Destructive by design.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down -v --remove-orphans
