"""SeaweedFS S3-gateway compatibility suite — MASTER_PROMPT §10.4.

Every behaviour here is one the rest of the platform silently assumes exists
(range requests for COG/PMTiles, real ListObjectsV2 pagination for the STAC
and Terria-catalog generators, anonymous read on public buckets for the
browser). If any of these fail, later milestones fail in confusing ways far
from the root cause — so they're verified here, in isolation, at M1.

Run with: bash scripts/test.sh (wraps venv + pytest) or `make test`.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import boto3
import pytest
import requests
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError

ENDPOINT = os.environ.get("SEAWEEDFS_ENDPOINT", "http://localhost:8333")
ACCESS_KEY = os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform")
SECRET_KEY = os.environ.get("SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate")

WAREHOUSE = "warehouse"
RAW = "raw"
ASSETS = "assets"
SERVING = "serving"


@pytest.fixture(scope="session")
def s3():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


@pytest.fixture(scope="session")
def anon_s3():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, signature_version=UNSIGNED),
    )


def test_buckets_exist(s3):
    names = {b["Name"] for b in s3.list_buckets()["Buckets"]}
    assert {WAREHOUSE, RAW, ASSETS, SERVING} <= names


def test_multipart_upload_large_object(s3):
    """>100MB object, uploaded via multipart, downloaded back with a matching checksum."""
    size = 120 * 1024 * 1024
    chunk = os.urandom(1024 * 1024)  # 1MB of random data, repeated
    key = f"compat/{uuid.uuid4()}.bin"

    hasher = hashlib.sha256()
    from io import BytesIO

    buf = BytesIO()
    written = 0
    while written < size:
        buf.write(chunk)
        hasher.update(chunk)
        written += len(chunk)
    buf.seek(0)
    expected_digest = hasher.hexdigest()

    from boto3.s3.transfer import TransferConfig

    transfer_config = TransferConfig(multipart_threshold=8 * 1024 * 1024, multipart_chunksize=8 * 1024 * 1024)
    s3.upload_fileobj(buf, RAW, key, Config=transfer_config)

    downloaded = BytesIO()
    s3.download_fileobj(RAW, key, downloaded)
    downloaded.seek(0)
    actual_digest = hashlib.sha256(downloaded.read()).hexdigest()

    assert actual_digest == expected_digest
    s3.delete_object(Bucket=RAW, Key=key)


def test_range_request(s3):
    """Range requests are what make COG/PMTiles usable — non-negotiable per §10.4."""
    key = f"compat/{uuid.uuid4()}.txt"
    body = b"0123456789" * 100  # 1000 bytes, known content
    s3.put_object(Bucket=RAW, Key=key, Body=body)

    resp = s3.get_object(Bucket=RAW, Key=key, Range="bytes=10-19")
    partial = resp["Body"].read()

    assert partial == body[10:20]
    assert resp["ContentLength"] == 10
    s3.delete_object(Bucket=RAW, Key=key)


def test_range_request_over_http(s3):
    """Same check via an unauthenticated raw HTTP range request, matching how a
    browser/TiTiler actually fetches a tile — so this must hit a publicly
    readable bucket (serving), not an authenticated-only one (raw)."""
    key = f"compat/{uuid.uuid4()}.txt"
    body = b"abcdefghij" * 100
    s3.put_object(Bucket=SERVING, Key=key, Body=body)

    url = f"{ENDPOINT}/{SERVING}/{key}"
    resp = requests.get(url, headers={"Range": "bytes=0-99"}, timeout=10)

    assert resp.status_code == 206, f"expected 206 Partial Content, got {resp.status_code}"
    assert resp.content == body[:100]
    s3.delete_object(Bucket=SERVING, Key=key)


def test_list_objects_v2_prefix_and_delimiter(s3):
    prefix = f"compat/listing-{uuid.uuid4()}/"
    for name in ["a.txt", "b.txt", "sub/c.txt"]:
        s3.put_object(Bucket=RAW, Key=prefix + name, Body=b"x")

    resp = s3.list_objects_v2(Bucket=RAW, Prefix=prefix, Delimiter="/")
    keys = {o["Key"] for o in resp.get("Contents", [])}
    common_prefixes = {p["Prefix"] for p in resp.get("CommonPrefixes", [])}

    assert keys == {prefix + "a.txt", prefix + "b.txt"}
    assert common_prefixes == {prefix + "sub/"}

    for name in ["a.txt", "b.txt", "sub/c.txt"]:
        s3.delete_object(Bucket=RAW, Key=prefix + name)


def test_list_objects_v2_pagination_beyond_1000_keys(s3):
    """The STAC and Terria-catalog generators page through listings; SeaweedFS
    must honour ListObjectsV2's 1000-key page limit and continuation tokens."""
    prefix = f"compat/pagination-{uuid.uuid4()}/"
    count = 1005

    def put(i: int):
        s3.put_object(Bucket=RAW, Key=f"{prefix}{i:05d}.txt", Body=b"")

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(put, range(count)))

    seen = set()
    token = None
    pages = 0
    while True:
        kwargs = {"Bucket": RAW, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        pages += 1
        seen.update(o["Key"] for o in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
        assert token, "IsTruncated=True but no NextContinuationToken returned"

    assert len(seen) == count
    assert pages >= 2, "expected pagination to span at least two pages for 1005 keys"

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(lambda i: s3.delete_object(Bucket=RAW, Key=f"{prefix}{i:05d}.txt"), range(count)))


def test_overwrite_read_after_write_consistency(s3):
    key = f"compat/{uuid.uuid4()}.txt"
    s3.put_object(Bucket=RAW, Key=key, Body=b"version-1")
    s3.put_object(Bucket=RAW, Key=key, Body=b"version-2")

    body = s3.get_object(Bucket=RAW, Key=key)["Body"].read()
    assert body == b"version-2"
    s3.delete_object(Bucket=RAW, Key=key)


def test_delete_object_and_delete_nonexistent(s3):
    key = f"compat/{uuid.uuid4()}.txt"
    s3.put_object(Bucket=RAW, Key=key, Body=b"x")
    s3.delete_object(Bucket=RAW, Key=key)

    with pytest.raises(ClientError):
        s3.head_object(Bucket=RAW, Key=key)

    # Deleting an already-absent key must not raise (S3 semantics: idempotent).
    s3.delete_object(Bucket=RAW, Key=key)


def test_anonymous_read_allowed_on_serving(s3, anon_s3):
    key = f"compat/{uuid.uuid4()}.txt"
    s3.put_object(Bucket=SERVING, Key=key, Body=b"public")

    body = anon_s3.get_object(Bucket=SERVING, Key=key)["Body"].read()
    assert body == b"public"
    s3.delete_object(Bucket=SERVING, Key=key)


def test_anonymous_read_refused_on_warehouse(anon_s3):
    with pytest.raises(ClientError) as exc_info:
        anon_s3.list_objects_v2(Bucket=WAREHOUSE)
    status = exc_info.value.response["ResponseMetadata"]["HTTPStatusCode"]
    assert status in (401, 403), f"expected anonymous access to warehouse to be refused, got HTTP {status}"


def test_cors_preflight_on_serving():
    url = f"{ENDPOINT}/{SERVING}/"
    resp = requests.options(
        url,
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "GET",
        },
        timeout=10,
    )
    assert resp.status_code < 400, f"CORS preflight failed with HTTP {resp.status_code}"
    assert "access-control-allow-origin" in {k.lower() for k in resp.headers}


@pytest.mark.skip(
    reason="Conditional-write reliance is Lakekeeper-specific; revisit once the M2 "
    "warehouse storage profile is wired up and we know whether it needs this."
)
def test_conditional_request_headers():
    pass
