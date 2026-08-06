"""The ingestion manifest contract (MASTER_PROMPT §8.1).

Every dataset in the platform — tabular, boundary, raster, web — is
described by one YAML manifest validated against `Manifest` below. The
loader is intentionally strict: a manifest missing `description`,
`caveats`, `owner`, `license` or `source_class` raises `ManifestError`
rather than loading with blanks, because those five fields are what keep
the Portal's trust badges and the Terria layer descriptions honest.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError


class ManifestError(Exception):
    """A manifest file failed to parse or validate."""


class SourceSpec(BaseModel):
    type: Literal["api_source", "file_source", "gee_source", "web_source"]
    endpoint: str
    auth: str = "none"


class ExtractSpec(BaseModel):
    mode: Literal["full", "incremental"]
    cursor: str | None = None
    schedule: str | None = None


class TargetSpec(BaseModel):
    modality: Literal["tabular", "vector", "raster"]
    format: Literal["iceberg", "geoparquet", "cog"]
    zone: str


class PublishSpec(BaseModel):
    pmtiles: bool = False
    stac_collection: str | None = None
    terria_group: Literal["Boundaries", "Indicators", "Earth observation"]
    region_provider: str | None = None


class QualitySpec(BaseModel):
    checks: list[str] = Field(default_factory=list)


class GovernanceSpec(BaseModel):
    owner: str
    classification: Literal["public", "internal", "restricted"]
    source_class: Literal["official", "derived", "modelled", "scraped"]
    license: str
    citation: str | None = None
    caveats: str


class Manifest(BaseModel):
    id: str
    title: str
    description: str
    source: SourceSpec
    extract: ExtractSpec
    target: TargetSpec
    publish: PublishSpec
    quality: QualitySpec = Field(default_factory=QualitySpec)
    governance: GovernanceSpec


# The subset of trust-critical fields the master prompt calls out by name.
# Enforced again here, on top of pydantic's own required-field checks, so
# the failure message points at the *reason* (trust badges / catalog
# descriptions) rather than a generic schema error.
_TRUST_CRITICAL_PATHS: tuple[tuple[str, ...], ...] = (
    ("description",),
    ("governance", "caveats"),
    ("governance", "owner"),
    ("governance", "license"),
    ("governance", "source_class"),
)


def _dotted(path: tuple[str, ...]) -> str:
    return ".".join(path)


def load_manifest(path: str | Path) -> Manifest:
    """Load and validate a manifest YAML file. Raises `ManifestError` on
    any missing/invalid field, naming the exact field that failed."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping")

    missing = [
        _dotted(field_path)
        for field_path in _TRUST_CRITICAL_PATHS
        if not _dig(raw, field_path)
    ]
    if missing:
        raise ManifestError(
            f"{path}: missing required field(s): {', '.join(missing)} "
            "(these back the Portal trust badges and catalog descriptions "
            "and cannot be blank)"
        )

    try:
        return Manifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"{path}: {exc}") from exc


def _dig(raw: dict, path: tuple[str, ...]) -> object | None:
    node: object = raw
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node
