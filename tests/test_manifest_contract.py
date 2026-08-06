"""Unit tests for the manifest contract (connectors/base). No Docker
services required — these only exercise YAML parsing and pydantic
validation."""

from pathlib import Path

import pytest
from connectors_base.manifest import ManifestError, load_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_MANIFEST = REPO_ROOT / "recipes" / "datasets" / "employment_indicators.yaml"


def test_loads_valid_manifest():
    manifest = load_manifest(GOOD_MANIFEST)
    assert manifest.id == "employment_indicators"
    assert manifest.governance.owner == "platform-team"
    assert manifest.source.type == "api_source"


@pytest.mark.parametrize(
    "remove_path",
    [
        "description",
        "governance.caveats",
        "governance.owner",
        "governance.license",
        "governance.source_class",
    ],
)
def test_rejects_manifest_missing_trust_critical_field(tmp_path, remove_path):
    import yaml

    raw = yaml.safe_load(GOOD_MANIFEST.read_text(encoding="utf-8"))
    node = raw
    parts = remove_path.split(".")
    for key in parts[:-1]:
        node = node[key]
    del node[parts[-1]]

    bad_manifest = tmp_path / "bad.yaml"
    bad_manifest.write_text(yaml.dump(raw), encoding="utf-8")

    with pytest.raises(ManifestError, match=parts[-1]):
        load_manifest(bad_manifest)


def test_rejects_invalid_source_type(tmp_path):
    import yaml

    raw = yaml.safe_load(GOOD_MANIFEST.read_text(encoding="utf-8"))
    raw["source"]["type"] = "carrier_pigeon"
    bad_manifest = tmp_path / "bad.yaml"
    bad_manifest.write_text(yaml.dump(raw), encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(bad_manifest)


def test_rejects_non_mapping_yaml(tmp_path):
    bad_manifest = tmp_path / "bad.yaml"
    bad_manifest.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(bad_manifest)
