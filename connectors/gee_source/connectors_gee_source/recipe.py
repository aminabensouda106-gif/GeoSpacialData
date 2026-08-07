"""The GEE recipe envelope (MASTER_PROMPT §8.2) — the *same* §8.1 manifest
envelope (`GeeRecipe` extends `Manifest`: `source.type` is still
"gee_source", `target.modality/format` still "raster"/"cog", governance
still required), plus `sources`/`domain`/`temporal`/`steps`/`refresh`.
Extending `Manifest` rather than redeclaring its fields is what lets
`PipelineRunRecorder` (built for §8.1 manifests) work unmodified for GEE
recipes too — it only ever reads `.id` and `.source.type`.

Two things the master prompt leaves as "..." in the abbreviated example
are made concrete here, since the validator needs them:
- `temporal.reduction.length`: the rolling window length in periods,
  used only when `reduction.window == "rolling"`.
- `refresh.window_periods`: how many trailing periods a `recompute_window`
  refresh reprocesses, used only when `incremental_strategy ==
  "recompute_window"`. The matrix's "(window >= rolling length)" note is
  enforced as `window_periods >= reduction.length`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from connectors_base.manifest import Manifest, ManifestError, check_trust_critical_fields
from pydantic import BaseModel, Field, ValidationError, model_validator


class GeeSourceRef(BaseModel):
    collection: str
    collection_version_pin: str
    bands: list[str]


class Domain(BaseModel):
    aoi: str
    crs: str
    scale_m: int
    grid_align_to: str


class Reduction(BaseModel):
    type: Literal["mean", "max", "percentile", "trend"]
    window: Literal["period", "rolling", "cumulative", "whole_series", "baseline_relative"]
    p: int | None = None
    length: int | None = None  # periods; required when window == "rolling"


class Temporal(BaseModel):
    grain: Literal["day", "month", "year"]
    reduction: Reduction


class Step(BaseModel):
    id: str
    op: str
    kind: Literal["transform", "classification"] = "transform"
    params: dict[str, Any] = Field(default_factory=dict)


class Refresh(BaseModel):
    cadence: str
    incremental_strategy: Literal[
        "append_period", "recompute_window", "stateful_merge", "split_baseline", "full_recompute"
    ]
    finality_lag_days: int
    revision_policy: str
    source_version_change: str
    window_periods: int | None = None  # periods; required when incremental_strategy == "recompute_window"


class RecipeError(ManifestError):
    pass


# `reduction.window` -> the only `incremental_strategy` value allowed for it.
# Enforced "exactly this" per MASTER_PROMPT §8.2's validator matrix. Kept as a
# module-level constant, not a class attribute, since pydantic v2 treats
# leading-underscore class attributes as private model fields.
ALLOWED_INCREMENTAL_STRATEGY: dict[str, str] = {
    "period": "append_period",
    "rolling": "recompute_window",
    "cumulative": "stateful_merge",
    "baseline_relative": "split_baseline",
    "whole_series": "full_recompute",
}


class GeeRecipe(Manifest):
    sources: list[GeeSourceRef]
    domain: Domain
    temporal: Temporal
    steps: list[Step]
    refresh: Refresh

    @model_validator(mode="after")
    def _validate_incremental_strategy(self) -> "GeeRecipe":
        window = self.temporal.reduction.window
        allowed = ALLOWED_INCREMENTAL_STRATEGY[window]
        actual = self.refresh.incremental_strategy
        if actual != allowed:
            raise ValueError(
                f"reduction.window={window!r} requires refresh.incremental_strategy="
                f"{allowed!r}, got {actual!r} (MASTER_PROMPT §8.2 validator matrix)"
            )

        if window == "rolling":
            if self.temporal.reduction.length is None:
                raise ValueError("reduction.window='rolling' requires reduction.length")
            if self.refresh.window_periods is None:
                raise ValueError(
                    "incremental_strategy='recompute_window' requires refresh.window_periods"
                )
            if self.refresh.window_periods < self.temporal.reduction.length:
                raise ValueError(
                    f"refresh.window_periods ({self.refresh.window_periods}) must be >= "
                    f"reduction.length ({self.temporal.reduction.length})"
                )
        return self

    @model_validator(mode="after")
    def _validate_append_period_has_no_cross_period_ops(self) -> "GeeRecipe":
        if self.refresh.incremental_strategy != "append_period":
            return self

        from connectors_gee_source.ops import get_op

        for step in self.steps:
            op = get_op(step.op)
            if op.cross_period_state:
                raise ValueError(
                    f"incremental_strategy='append_period' but step {step.id!r} uses op "
                    f"{step.op!r}, which declares cross_period_state=True — append_period "
                    "can't see the state such an op depends on"
                )
        return self

    @model_validator(mode="after")
    def _validate_classification_steps_are_pinned(self) -> "GeeRecipe":
        for step in self.steps:
            if step.kind != "classification":
                continue
            model_hash = step.params.get("model_hash")
            if not model_hash or not str(model_hash).startswith("sha256:"):
                raise ValueError(
                    f"classification step {step.id!r} must pin its model artifact via "
                    "params.model_hash (e.g. 'sha256:...')"
                )
        return self


def load_recipe(path: str | Path) -> GeeRecipe:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RecipeError(f"{path}: invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise RecipeError(f"{path}: recipe must be a YAML mapping")

    check_trust_critical_fields(raw, path)

    try:
        return GeeRecipe.model_validate(raw)
    except ValidationError as exc:
        raise RecipeError(f"{path}: {exc}") from exc
