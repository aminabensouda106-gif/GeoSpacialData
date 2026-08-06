"""M2 STOP GATE asset: proves Dagster -> PyIceberg -> Lakekeeper -> SeaweedFS
end to end. Writes bronze.hello and reports where it landed on S3."""

import pyarrow as pa
from dagster import AssetExecutionContext, MaterializeResult, asset
from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError

from platform_orchestration.resources.iceberg import get_catalog

HELLO_SCHEMA = pa.schema([("id", pa.int64()), ("message", pa.string())])
TABLE_IDENTIFIER = "bronze.hello"


@asset(key_prefix="bronze", name="hello")
def hello(context: AssetExecutionContext) -> MaterializeResult:
    catalog = get_catalog()

    try:
        catalog.create_namespace("bronze")
    except NamespaceAlreadyExistsError:
        pass

    data = pa.table(
        {"id": [1, 2, 3], "message": ["hello", "from", "dagster"]}, schema=HELLO_SCHEMA
    )

    try:
        table = catalog.create_table(TABLE_IDENTIFIER, schema=HELLO_SCHEMA)
        table.append(data)
    except TableAlreadyExistsError:
        table = catalog.load_table(TABLE_IDENTIFIER)
        table.overwrite(data)

    metadata_location = table.metadata_location
    context.log.info(f"Wrote {data.num_rows} rows to {TABLE_IDENTIFIER} at {table.location()}")
    context.log.info(f"Metadata location: {metadata_location}")

    return MaterializeResult(
        metadata={
            "row_count": data.num_rows,
            "table_location": table.location(),
            "metadata_location": metadata_location,
        }
    )
