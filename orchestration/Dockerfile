FROM python:3.12-slim

# GDAL/OGR for file_source (Dataset B, M3); build-essential+git are needed
# to build tippecanoe from source in a later layer (M3 PMTiles step).
RUN apt-get update && apt-get install -y --no-install-recommends \
      gdal-bin \
      libgdal-dev \
      build-essential \
      git \
      libsqlite3-dev \
      zlib1g-dev \
      && rm -rf /var/lib/apt/lists/*

# tippecanoe has no Debian package on bookworm; build it from source once,
# in its own layer so it isn't rebuilt when only Python code changes.
RUN git clone --depth 1 https://github.com/felt/tippecanoe.git /tmp/tippecanoe \
    && make -C /tmp/tippecanoe -j"$(nproc)" \
    && make -C /tmp/tippecanoe install \
    && rm -rf /tmp/tippecanoe

WORKDIR /opt/dagster/app

# Build context is the repo root (see docker-compose.yml) so this image can
# pip-install the connectors/ packages and reach sample-data/ and recipes/
# at their normal repo-relative paths, both at build time and at runtime.
# sample-data/ and recipes/ are copied *after* the pip install below —
# they're data, not Python packages the install depends on, so editing a
# fixture or a recipe YAML doesn't invalidate (and force a slow re-run of)
# the pip install layer.
COPY orchestration/pyproject.toml ./orchestration/pyproject.toml
COPY orchestration/platform_orchestration ./orchestration/platform_orchestration
COPY connectors ./connectors

RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache \
    -e ./connectors/base \
    -e ./connectors/api_source \
    -e ./connectors/file_source \
    -e ./connectors/gee_source \
    -e ./orchestration

COPY sample-data ./sample-data
COPY recipes ./recipes

COPY orchestration/dagster.yaml /opt/dagster/dagster_home/dagster.yaml
ENV DAGSTER_HOME=/opt/dagster/dagster_home
ENV PLATFORM_REPO_ROOT=/opt/dagster/app

EXPOSE 3000

CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-m", "platform_orchestration.definitions"]
