"""Synthetic Sentinel-2-like fixture scenes for the `gee_source` connector
(Dataset C), standing in for real Earth Engine pulls so the recipe
pipeline runs with zero EE credentials (MASTER_PROMPT M4 — `provenance.
mode = "fixture"`).

`scenes_catalog.json` in this directory is the mutable "what EE has right
now" state: each period maps to the scene IDs currently available for it.
Editing that file to add a scene to an already-published period is
exactly how STOP GATE 4's late-arriving-asset test is performed — the
connector's set-difference change detection is what decides that only
that one period needs to reprocess.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

FIXTURES_DIR = Path(__file__).resolve().parent


def load_scene_catalog() -> dict[str, list[str]]:
    catalog_path = FIXTURES_DIR / "scenes_catalog.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def generate_scene(scene_id: str, shape: tuple[int, int] = (64, 64)) -> dict[str, np.ndarray]:
    """Deterministic per-scene synthetic bands, seeded from the scene ID
    so the same ID always yields the same pixels (a real acquisition
    would be equally immutable)."""
    seed = int(hashlib.sha256(scene_id.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    red = rng.uniform(0.05, 0.25, size=shape).astype(np.float32)
    nir = rng.uniform(0.20, 0.55, size=shape).astype(np.float32)
    return {"B4": red, "B8": nir}
