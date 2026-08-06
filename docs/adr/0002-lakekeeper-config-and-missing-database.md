# 0002 — Lakekeeper: verified config keys, image tag, and a gap in §4's DB list

**Status:** Accepted (M2)

## Context

The master prompt explicitly flags Lakekeeper's storage-profile config keys as
likely to have changed across versions and says to verify against current
docs rather than guess.

## What was verified

- **Image**: `quay.io/lakekeeper/catalog`. The project's own example compose
  file defaults to `:latest-main` (a nightly-style tag); for a POC that
  needs to keep working, a real release tag is safer — pinned to `v0.11.1`,
  the latest stable release found at build time.
- **Bootstrap flow**: `POST /management/v1/bootstrap` with
  `{"accept-terms-of-use": true}`, then `POST /management/v1/warehouse` with
  a JSON body — confirmed from Lakekeeper's own `examples/minimal/` compose
  project in its GitHub repo, not just prose docs.
- **S3-compatible storage-profile schema**: fetched
  `examples/minimal/create-default-warehouse.json` directly from the
  Lakekeeper repo — and it turns out **the project's own official example
  targets SeaweedFS specifically** (`"endpoint": "http://seaweedfs:8333"`).
  That's about as authoritative a source as exists for this exact
  integration, so `infra/lakekeeper/create-default-warehouse.json` mirrors
  its shape closely: `flavor: "s3-compat"`, `path-style-access: true`,
  `region: "local-01"` (arbitrary — s3-compat ignores AWS region rules),
  `sts-enabled: true` with `sts-endpoint` pointed at the same SeaweedFS
  gateway, and a placeholder `sts-role-arn` (the docs confirm this field is
  ignored for the `s3-compat` flavor, so any well-formed ARN string works).
- **Field-name discrepancy — the summarized doc page was actually right**:
  a doc-page summary suggested `aws-access-key-id`/`aws-secret-access-key`
  for `storage-credential`; the repo's `examples/minimal/` JSON file used
  `access-key-id`/`secret-access-key` instead. Trusted the repo file as more
  authoritative and got it wrong: the running `v0.11.1` server rejected it
  with `422 Failed to deserialize... missing field 'aws-access-key-id'`.
  The example file in `main` is evidently ahead of (or otherwise diverged
  from) the `v0.11.1` release schema. Corrected to `aws-access-key-id`/
  `aws-secret-access-key`, confirmed working (`201` on warehouse creation).
  Lesson for later milestones: an example file fetched from a project's
  `main` branch is not automatically more trustworthy than doc prose for a
  *pinned release* — both need reconciling against whatever version is
  actually pinned, and the real server's error response is the tiebreaker.
- **`sts-enabled: true` does not work against SeaweedFS**: warehouse
  creation with `sts-enabled: true` (mirroring the repo's own SeaweedFS
  example) failed with `412 ShortTermCredentialError` — Lakekeeper's
  AssumeRole call to SeaweedFS's STS endpoint got back an HTTP `503
  Service Unavailable` from SeaweedFS itself. This is the exact kind of
  compatibility gap §10.4 warned about, just in Lakekeeper's STS path
  rather than the S3 API compat suite. Set `sts-enabled: false` instead —
  the POC doesn't need short-term vended credentials; Lakekeeper and every
  reader (PyIceberg, DuckDB) use the same static `platform` credentials
  directly. Confirmed working (`201` on warehouse creation, and the M2
  STOP GATE materialization below).
- **PyIceberg ↔ Lakekeeper**: REST catalog URI is `http://<host>:8181/catalog`
  (the `/catalog` suffix is Lakekeeper's Iceberg REST mount point, distinct
  from `/management` for the admin API used above). FileIO properties are
  the standard PyIceberg `s3.endpoint` / `s3.access-key-id` /
  `s3.secret-access-key` / `s3.path-style-access` / `s3.region` keys.

## A gap in the master prompt's own service table

§4 lists exactly four Postgres databases: `pgstac`, `dagster`, `cube`,
`platform`. Lakekeeper needs its own Postgres-backed metadata store
(`LAKEKEEPER__PG_DATABASE_URL_READ`/`_WRITE`) to run at all — there's no
fifth database anywhere in the doc for it. This isn't a new *service* (rule
#8 only restricts the service list, and Lakekeeper is already in it) — it's
a missing entry in a table describing a service already approved. Added
`lakekeeper` to `POSTGRES_MULTIPLE_DATABASES` rather than stopping to ask,
on the reasoning that filling a table gap for an already-approved service is
different from adding scope. Flagged here so it isn't a silent deviation.

## A second gap: no migration step

Neither the master prompt's example command nor the doc pages fetched
mentioned that Lakekeeper's schema must be migrated before `serve` will
work. Running `serve` straight against a freshly-created `lakekeeper`
database failed with `relation "server" does not exist`. Running
`docker run quay.io/lakekeeper/catalog:v0.11.1 --help` showed the actual
CLI: `migrate`, `wait-for-db`, `serve` ("The database must be migrated
before running the server"), `healthcheck`. Added a one-shot
`lakekeeper-migrate` service (`command: ["migrate"]`) that `lakekeeper` now
depends on via `condition: service_completed_successfully`, mirroring the
`seaweedfs-init`/`pgstac-init` one-shot pattern already used elsewhere in
this compose file.

## Decision

- Pin `quay.io/lakekeeper/catalog:v0.11.1`.
- `infra/lakekeeper/create-default-warehouse.json` and `init-lakekeeper.sh`
  as described above; warehouse name `poc`, bucket `warehouse`, key-prefix
  `iceberg`.
- Fifth Postgres database `lakekeeper`, created by the same
  `init-multiple-db.sh` mechanism from M1 — no new init logic needed, just
  one more name in the comma-separated list.

## STOP GATE 2 — confirmed working end to end

Verified on a from-scratch `scripts/reset.sh && scripts/bootstrap.sh` run
(no manual steps): Dagster materializes `bronze.hello` → Parquet + Iceberg
metadata land under `s3://warehouse/iceberg/...` → DuckDB reads it back
via `iceberg_scan()` pointed at the table's current `metadata-location`
(fetched from Lakekeeper's REST API rather than assumed). See
`notebooks/01_verify_m2_lakehouse.ipynb`.

Exact DuckDB settings that worked against SeaweedFS:

```sql
INSTALL httpfs; LOAD httpfs;
INSTALL iceberg; LOAD iceberg;
SET s3_endpoint='seaweedfs:8333';
SET s3_use_ssl=false;
SET s3_url_style='path';
SET s3_region='local-01';
SET s3_access_key_id='platform';
SET s3_secret_access_key='platform-dev-secret-please-rotate';
```

`s3_url_style='path'` is the load-bearing one (§10.3's path-style rule
applies identically here); `s3_region` is arbitrary since SeaweedFS ignores
AWS region validation, but DuckDB still requires the setting to be present.

## Consequences

- If Lakekeeper's `s3-compat` flavor turns out not to fully support SeaweedFS's
  STS surface (`sts-enabled: true` calls a real AssumeRole-shaped endpoint),
  the fallback is `sts-enabled: false` with static credentials passed through
  directly — noted here so it's not a mystery if M3's real ingestion writes
  hit an auth error that M2's smaller hello-world write didn't exercise.
