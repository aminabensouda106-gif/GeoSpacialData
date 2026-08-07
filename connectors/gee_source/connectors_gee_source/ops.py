"""The registered op library (MASTER_PROMPT §8.2): a GEE recipe's `steps`
are ordered calls into ops registered here, never arbitrary code. Each op
declares two things the validator needs:

- `period_decomposable`: can this op run independently per period (so a
  refresh only touches the periods that changed), or does it need the
  whole series at once (e.g. a trend fit)?
- `cross_period_state`: does this op accumulate state across periods
  (e.g. a running baseline)? `append_period` is rejected for any recipe
  using such an op, because appending one period at a time can't see the
  state a cross-period op depends on.

Ops operate on `numpy` arrays; a step's `params` are passed as kwargs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np

# How the interpreter (connectors_gee_source.pipeline) feeds this op's
# `fn` and what it does with the result:
#   scene_transform  — dict[band -> array] -> dict[band -> array], applied
#                       to every scene independently (e.g. cloud masking).
#   scene_to_array   — dict[band -> array] -> array, applied to every
#                       scene independently, replacing the per-scene dicts
#                       with a per-scene array (e.g. a band index).
#   temporal_reduce  — list[array] -> array, collapsing all of a period's
#                       per-scene arrays into the period's composite.
OpKind = Literal["scene_transform", "scene_to_array", "temporal_reduce"]


@dataclass(frozen=True)
class Op:
    name: str
    kind: OpKind
    period_decomposable: bool
    cross_period_state: bool
    fn: Callable[..., np.ndarray]


def _s2_cloud_shadow_mask(scene: dict[str, np.ndarray], **params) -> dict[str, np.ndarray]:
    """Fixture stand-in: real EE data would mask cloud/shadow pixels via
    the collection's QA band. Synthetic fixture scenes have no clouds, so
    this is a structural pass-through that documents where the real mask
    would apply."""
    return scene


def _normalized_difference(scene: dict[str, np.ndarray], *, nir: str, red: str) -> np.ndarray:
    nir_band = scene[nir].astype(np.float64)
    red_band = scene[red].astype(np.float64)
    denom = nir_band + red_band
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(denom != 0, (nir_band - red_band) / denom, 0.0)
    return result.astype(np.float32)


def _temporal_reduce(arrays: list[np.ndarray], *, reducer: str, p: int | None = None) -> np.ndarray:
    stack = np.stack(arrays, axis=0)
    if reducer == "mean":
        return stack.mean(axis=0).astype(np.float32)
    if reducer == "max":
        return stack.max(axis=0).astype(np.float32)
    if reducer == "percentile":
        if p is None:
            raise ValueError("percentile reducer requires params.p")
        return np.percentile(stack, p, axis=0).astype(np.float32)
    raise ValueError(f"unknown reducer: {reducer!r}")


OPS: dict[str, Op] = {
    "s2_cloud_shadow_mask": Op(
        name="s2_cloud_shadow_mask",
        kind="scene_transform",
        period_decomposable=True,
        cross_period_state=False,
        fn=_s2_cloud_shadow_mask,
    ),
    "normalized_difference": Op(
        name="normalized_difference",
        kind="scene_to_array",
        period_decomposable=True,
        cross_period_state=False,
        fn=_normalized_difference,
    ),
    "temporal_reduce": Op(
        name="temporal_reduce",
        kind="temporal_reduce",
        period_decomposable=True,
        cross_period_state=False,
        fn=_temporal_reduce,
    ),
}


class UnknownOpError(Exception):
    pass


def get_op(name: str) -> Op:
    try:
        return OPS[name]
    except KeyError:
        raise UnknownOpError(
            f"op {name!r} is not registered; available ops: {sorted(OPS)}"
        ) from None
