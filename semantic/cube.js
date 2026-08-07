module.exports = {
  contextToAppId: () => "GEODATA_POC",
  scheduledRefreshContexts: () => [{}],
  driverFactory: () => ({
    type: "duckdb",
    initSql: "SET s3_url_style='path';",
  }),
};
