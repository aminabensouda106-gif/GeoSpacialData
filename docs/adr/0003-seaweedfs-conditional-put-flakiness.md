# 0003 — SeaweedFS all-in-one: intermittent AccessDenied on conditional PUT

**Status:** Accepted (M3)

## Context

While verifying M3's STOP GATE 3, a `PipelineRunRecorder` append to
`platform.pipeline_runs` (via PyIceberg's `table.append()`) intermittently
failed with `botocore.errorfactory.AccessDenied: ... PutObject ... Access
Denied`, even though the exact same code path had just succeeded twice in a
row for the two real dataset runs, and a plain unconditional `put_object`
to the same bucket succeeded immediately afterwards.

## What was verified

- PyIceberg's manifest/metadata writes go through `s3fs`, which — per
  `s3fs.core.S3File.commit` — sends an `IfNoneMatch: "*"` conditional header
  on one-shot PUTs whenever the file is opened in exclusive-create (`"x"`)
  mode, which PyIceberg uses to make commits atomic.
- A fresh, definitely-nonexistent key PUT with `IfNoneMatch="*"` via raw
  boto3 succeeded, ruling out a blanket "SeaweedFS doesn't support
  `If-None-Match`" incompatibility.
- `docker compose logs seaweedfs` shows periodic, unprompted entries during
  the same window:
  ```
  FILER LOCK: Error - name=s3.leader error=lock: non-empty token on a new lock
  Lost lock s3.leader
  ```
  recurring roughly every 5 minutes, which is the all-in-one filer's
  internal S3-leader election churning. The failed `AccessDenied` occurred
  in this window; retrying the identical write immediately after succeeded.

## Decision

Treat this as a known stability quirk of running SeaweedFS as a single
all-in-one container (master+volume+filer+S3 in one process), not a bug in
the ingestion framework or a genuine `If-None-Match` incompatibility. No
code workaround is applied for the POC: PyIceberg's own commit path already
retries on `CommitFailedException`-class errors, and a bare `AccessDenied`
surfaces as a normal Python exception that `PipelineRunRecorder` already
records as a failed run rather than silently losing data.

## Consequences

- If a connector run fails with `AccessDenied` on an S3 PUT during an
  Iceberg commit, retry once before treating it as a real bug — check
  `docker compose logs seaweedfs` for `Lost lock s3.leader` in the same
  window to confirm this known cause before debugging application code.
- Should this resurface with enough frequency to affect the demo, the fix
  is almost certainly a SeaweedFS version bump or moving off the
  all-in-one topology (separate master/volume/filer/S3 processes) rather
  than anything in `connectors/` — flagged here so it isn't rediscovered
  from scratch.
