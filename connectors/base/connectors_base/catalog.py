"""PyIceberg catalog handle, shared by the run-record emitter and every
connector that registers a table. Mirrors
`orchestration/platform_orchestration/resources/iceberg.py` — duplicated
rather than imported because `connectors/*` must not depend on
`orchestration` (dependency runs the other way: Dagster assets call into
connectors, not vice versa).
"""

import os

from pyiceberg.catalog import Catalog, load_catalog


def get_catalog() -> Catalog:
    return load_catalog(
        "lakekeeper",
        **{
            "uri": os.environ.get("LAKEKEEPER_URI", "http://lakekeeper:8181/catalog"),
            "warehouse": os.environ.get("LAKEKEEPER_WAREHOUSE", "poc"),
            "s3.endpoint": os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333"),
            "s3.access-key-id": os.environ.get("SEAWEEDFS_ACCESS_KEY", "platform"),
            "s3.secret-access-key": os.environ.get(
                "SEAWEEDFS_SECRET_KEY", "platform-dev-secret-please-rotate"
            ),
            "s3.path-style-access": "true",
            "s3.region": "local-01",
        },
    )
