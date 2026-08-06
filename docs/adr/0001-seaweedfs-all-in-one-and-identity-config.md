# 0001 — SeaweedFS: single-container `weed server`, static dev identities

**Status:** Accepted (M1)

## Context

The master prompt requires SeaweedFS (not MinIO) as the S3-compatible object
store, run as a single all-in-one container for the POC, with a named
`platform` identity for services and an `anonymous` identity limited to
`Read` on `assets`/`serving`.

Two things needed verifying before writing config, per the doc's own rule
("verify, don't guess"):

1. Does `weed server` actually support combining master+volume+filer+S3 in
   one process via `-filer -s3` flags, as the doc's example command assumes?
2. What is the real schema for the S3 identity config (`s3.json`), and does
   SeaweedFS support a genuinely anonymous (unauthenticated) identity scoped
   to specific buckets, or only an all-or-nothing "Allow-All Mode"?

## What was verified

- `docker run --rm chrislusf/seaweedfs:latest server -h` confirms `-dir`,
  `-filer`, `-s3`, `-s3.config`, `-s3.port`, and `-master.volumeSizeLimitMB`
  all exist as top-level flags of the `server` subcommand — the doc's
  example command is valid as written.
- The image is Alpine-based with both `wget` and `curl` present, so the
  master's `/cluster/status` healthcheck (doc §10.1: check the master
  endpoint, not port 8333 alone — the S3 gateway accepts connections before
  the filer is ready) can use `wget` without adding tooling.
- SeaweedFS's own wiki does not publish one canonical worked example for a
  scoped anonymous identity. Multiple independent community sources
  (GitHub issues/discussions on `seaweedfs/seaweedfs`) converge on the same
  pattern: an identity object named `"anonymous"` with **no** `credentials`
  array and bucket-scoped actions written as `"Read:<bucket>"`. This is not
  as strong as a first-party doc citation, so it is treated as best-effort
  and is *empirically* re-verified by
  `tests/test_seaweedfs_compat.py::test_anonymous_read_allowed_on_serving`
  and `::test_anonymous_read_refused_on_warehouse` at every `make test` run
  — if the community pattern is wrong, the compat suite catches it rather
  than it silently failing downstream (e.g. in TerriaMap's browser fetches
  at M7).
- `PutBucketCors`/`GetBucketCors`/`DeleteBucketCors` are implemented in
  SeaweedFS's S3 gateway, so `seaweedfs-init` can call
  `aws s3api put-bucket-cors` directly instead of needing a config-file
  workaround. One GitHub discussion flags that CORS *enforcement* for some
  browser flows (presigned POST uploads) has known gaps — not something
  this POC uses, but worth remembering if a later milestone needs presigned
  uploads from the browser.

## Decision

- Run SeaweedFS as one container: `weed server -dir=/data
  -master.volumeSizeLimitMB=1024 -filer -s3 -s3.config=/etc/seaweedfs/s3.json
  -s3.port=8333`, matching the master prompt exactly.
- `infra/seaweedfs/s3.json` defines a `platform` identity with static
  dev-only credentials (`platform` / `platform-dev-secret-please-rotate`)
  and an `anonymous` identity with `["Read:assets", "Read:serving"]`.
- Credentials are duplicated (once in `s3.json`, once in `.env.example`)
  rather than templated at container start, because SeaweedFS doesn't
  expand env vars inside `s3.json` and adding an envsubst step for a
  POC-only static secret wasn't worth the extra moving part. If this ever
  needs to be real, `s3.json` and `.env` both need updating — flagged here
  so it isn't a surprise later.

## Consequences

- The compat suite is load-bearing, not decorative: it's the actual
  verification that the guessed-at anonymous-identity pattern works, not
  just a nice-to-have test.
- Any change to SeaweedFS's identity schema in a future version would be
  caught by `make test` before it reached TiTiler/Terria/the Portal, all of
  which depend on `assets`/`serving` being anonymously readable.
