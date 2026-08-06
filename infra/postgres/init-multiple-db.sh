#!/bin/bash
# Creates the additional databases listed in POSTGRES_MULTIPLE_DATABASES.
# POSTGRES_DB (created automatically by the base image) is one of them; this
# script no-ops for any name that already exists.
set -e

create_database() {
  local database=$1
  echo "Ensuring database '$database' exists"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE "$database"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
  echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
  for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
    create_database "$db"
  done
  echo "Multiple databases created"
fi
