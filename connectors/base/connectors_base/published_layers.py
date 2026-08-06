"""The published-layers registry (`platform.published_layers`), MASTER_PROMPT
M3. One row per PMTiles layer published to `s3://serving/pmtiles/`,
recording its bounds, zoom range, feature ID property and source dataset.
The Terria catalog generator (M7) reads this table to build the vector
tile members of the generated catalog — never by hand.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pyarrow as pa
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError

from connectors_base.catalog import get_catalog

TABLE_IDENTIFIER = "platform.published_layers"

PUBLISHED_LAYERS_SCHEMA = pa.schema(
    [
        ("layer_id", pa.string()),
        ("source_dataset_id", pa.string()),
        ("pmtiles_path", pa.string()),
        ("bbox_minx", pa.float64()),
        ("bbox_miny", pa.float64()),
        ("bbox_maxx", pa.float64()),
        ("bbox_maxy", pa.float64()),
        ("min_zoom", pa.int32()),
        ("max_zoom", pa.int32()),
        ("id_property", pa.string()),
        ("published_at", pa.timestamp("us", tz="UTC")),
    ]
)


def register_layer(
    *,
    layer_id: str,
    source_dataset_id: str,
    pmtiles_path: str,
    bbox: tuple[float, float, float, float],
    min_zoom: int,
    max_zoom: int,
    id_property: str,
) -> None:
    minx, miny, maxx, maxy = bbox
    row = pa.table(
        {
            "layer_id": [layer_id],
            "source_dataset_id": [source_dataset_id],
            "pmtiles_path": [pmtiles_path],
            "bbox_minx": [minx],
            "bbox_miny": [miny],
            "bbox_maxx": [maxx],
            "bbox_maxy": [maxy],
            "min_zoom": [min_zoom],
            "max_zoom": [max_zoom],
            "id_property": [id_property],
            "published_at": [datetime.now(timezone.utc)],
        },
        schema=PUBLISHED_LAYERS_SCHEMA,
    )

    catalog = get_catalog()
    try:
        catalog.create_namespace("platform")
    except NamespaceAlreadyExistsError:
        pass
    try:
        table = catalog.create_table(TABLE_IDENTIFIER, schema=PUBLISHED_LAYERS_SCHEMA)
    except TableAlreadyExistsError:
        table = catalog.load_table(TABLE_IDENTIFIER)
    table.append(row)
