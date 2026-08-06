"""Shared helper for obtaining a PyIceberg catalog backed by Lakekeeper + SeaweedFS.

Not yet a Dagster ConfigurableResource — kept as a plain function until M3,
when the ingestion framework's per-dataset assets need it wired through
Dagster's resource system rather than called ad hoc.
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
