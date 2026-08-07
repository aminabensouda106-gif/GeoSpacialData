"""Contributing-asset manifest + set-difference change detection
(MASTER_PROMPT §8.2): for each published period, record the exact source
asset IDs that went into it. A refresh recomputes the current asset-ID
set for each period and compares by hash, not by date — an asset that
existed all along isn't a change; a genuinely new asset ID is, even if
its own timestamp is old (a late-arriving scene from a prior date still
counts)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.compute as pc
from connectors_base.catalog import get_catalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError, NoSuchTableError, TableAlreadyExistsError

TABLE_IDENTIFIER = "platform.gee_contributing_assets"

SCHEMA = pa.schema(
    [
        ("dataset_id", pa.string()),
        ("period", pa.string()),
        ("asset_ids", pa.string()),  # JSON-encoded, sorted list
        ("asset_ids_hash", pa.string()),
        ("published_at", pa.timestamp("us", tz="UTC")),
    ]
)


def hash_asset_ids(asset_ids: list[str]) -> str:
    joined = ",".join(sorted(asset_ids))
    return f"sha256:{hashlib.sha256(joined.encode('utf-8')).hexdigest()}"


def latest_hash(dataset_id: str, period: str) -> str | None:
    catalog = get_catalog()
    try:
        table = catalog.load_table(TABLE_IDENTIFIER)
    except NoSuchTableError:
        return None

    arrow_table = table.scan().to_arrow()
    mask = pc.and_(
        pc.equal(arrow_table["dataset_id"], dataset_id),
        pc.equal(arrow_table["period"], period),
    )
    filtered = arrow_table.filter(mask)
    if filtered.num_rows == 0:
        return None

    order = pc.sort_indices(filtered, sort_keys=[("published_at", "descending")])
    latest = filtered.take(order[:1]).to_pylist()[0]
    return latest["asset_ids_hash"]


def record(dataset_id: str, period: str, asset_ids: list[str]) -> str:
    """Append a new contributing-asset manifest row and return its hash."""
    asset_hash = hash_asset_ids(asset_ids)
    row = pa.table(
        {
            "dataset_id": [dataset_id],
            "period": [period],
            "asset_ids": [json.dumps(sorted(asset_ids))],
            "asset_ids_hash": [asset_hash],
            "published_at": [datetime.now(timezone.utc)],
        },
        schema=SCHEMA,
    )

    catalog = get_catalog()
    try:
        catalog.create_namespace("platform")
    except NamespaceAlreadyExistsError:
        pass
    try:
        table = catalog.create_table(TABLE_IDENTIFIER, schema=SCHEMA)
    except TableAlreadyExistsError:
        table = catalog.load_table(TABLE_IDENTIFIER)
    table.append(row)
    return asset_hash
