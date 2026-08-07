"""Load `sample-data/gee_fixtures/generator.py` by file path — `sample-data/`
holds fixtures and small scripts shared across connectors, not an
installed package (same pattern as `connectors_api_source`)."""

from __future__ import annotations

import importlib.util

from connectors_base.repo_paths import repo_root


def _load_module():
    path = repo_root() / "sample-data" / "gee_fixtures" / "generator.py"
    spec = importlib.util.spec_from_file_location("gee_fixtures_generator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_scene_catalog() -> dict[str, list[str]]:
    return _load_module().load_scene_catalog()


def generate_scene(scene_id: str, shape: tuple[int, int] = (64, 64)) -> dict:
    return _load_module().generate_scene(scene_id, shape)
