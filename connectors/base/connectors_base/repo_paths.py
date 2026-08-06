"""Locate the repo root from inside a connector, so connectors can reach
`sample-data/` and `recipes/` without hardcoding a layout that differs
between local dev and the Dagster container image."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("PLATFORM_REPO_ROOT")
    if env:
        return Path(env)

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "sample-data").is_dir() and (parent / "recipes").is_dir():
            return parent

    raise RuntimeError(
        "Could not locate the platform repo root by walking up from "
        f"{here}; set PLATFORM_REPO_ROOT explicitly."
    )
