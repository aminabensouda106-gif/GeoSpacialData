"""The recipe interpreter: runs a `GeeRecipe`'s ordered `steps` over a
period's fixture scenes, dispatching each step by its op's declared
`kind` (MASTER_PROMPT §8.2 — "an ordered list, each `op` registered and
tested"). No step is ever arbitrary code; every op comes from the
registry in `ops.py`.
"""

from __future__ import annotations

import numpy as np

from connectors_gee_source import fixtures
from connectors_gee_source.ops import get_op
from connectors_gee_source.recipe import GeeRecipe


def run_period(recipe: GeeRecipe, asset_ids: list[str]) -> np.ndarray:
    scenes = [fixtures.generate_scene(asset_id) for asset_id in asset_ids]
    per_scene_arrays: list[np.ndarray] | None = None

    for step in recipe.steps:
        op = get_op(step.op)

        if op.kind == "scene_transform":
            scenes = [op.fn(scene, **step.params) for scene in scenes]
        elif op.kind == "scene_to_array":
            per_scene_arrays = [op.fn(scene, **step.params) for scene in scenes]
        elif op.kind == "temporal_reduce":
            if per_scene_arrays is None:
                raise RuntimeError(
                    f"step {step.id!r} (op={step.op!r}, kind=temporal_reduce) ran before "
                    "any scene_to_array step produced per-scene arrays to reduce"
                )
            per_scene_arrays = [op.fn(per_scene_arrays, **step.params)]
        else:  # pragma: no cover - exhaustive over OpKind
            raise RuntimeError(f"unhandled op kind: {op.kind!r}")

    if per_scene_arrays is None or len(per_scene_arrays) != 1:
        raise RuntimeError(
            "recipe steps did not converge to a single composite array — "
            "check that the last step is a temporal_reduce op"
        )
    return per_scene_arrays[0]
