"""Unit tests for the GEE recipe validator (MASTER_PROMPT §8.2). No Docker
services required — pure pydantic validation."""

from pathlib import Path

import pytest
import yaml
from connectors_gee_source.ops import Op, OPS
from connectors_gee_source.recipe import RecipeError, load_recipe

REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_RECIPE = REPO_ROOT / "recipes" / "gee" / "ndvi_composite.yaml"


def _load_raw() -> dict:
    return yaml.safe_load(GOOD_RECIPE.read_text(encoding="utf-8"))


def _write(tmp_path: Path, raw: dict) -> Path:
    path = tmp_path / "recipe.yaml"
    path.write_text(yaml.dump(raw), encoding="utf-8")
    return path


def test_loads_valid_recipe():
    recipe = load_recipe(GOOD_RECIPE)
    assert recipe.id == "ndvi_composite"
    assert recipe.refresh.incremental_strategy == "append_period"


@pytest.mark.parametrize(
    "window,wrong_strategy",
    [
        ("period", "full_recompute"),
        ("rolling", "append_period"),
        ("cumulative", "append_period"),
        ("baseline_relative", "append_period"),
        ("whole_series", "append_period"),
    ],
)
def test_rejects_mismatched_window_and_strategy(tmp_path, window, wrong_strategy):
    raw = _load_raw()
    raw["temporal"]["reduction"]["window"] = window
    raw["refresh"]["incremental_strategy"] = wrong_strategy
    if window == "rolling":
        raw["temporal"]["reduction"]["length"] = 3
        raw["refresh"]["window_periods"] = 3
    with pytest.raises(RecipeError, match="validator matrix"):
        load_recipe(_write(tmp_path, raw))


def test_rolling_requires_length(tmp_path):
    raw = _load_raw()
    raw["temporal"]["reduction"]["window"] = "rolling"
    raw["refresh"]["incremental_strategy"] = "recompute_window"
    raw["refresh"]["window_periods"] = 3
    with pytest.raises(RecipeError, match="reduction.length"):
        load_recipe(_write(tmp_path, raw))


def test_rolling_window_periods_must_be_at_least_length(tmp_path):
    raw = _load_raw()
    raw["temporal"]["reduction"]["window"] = "rolling"
    raw["temporal"]["reduction"]["length"] = 6
    raw["refresh"]["incremental_strategy"] = "recompute_window"
    raw["refresh"]["window_periods"] = 3
    with pytest.raises(RecipeError, match="window_periods"):
        load_recipe(_write(tmp_path, raw))


def test_rolling_valid_when_window_periods_ge_length(tmp_path):
    raw = _load_raw()
    raw["temporal"]["reduction"]["window"] = "rolling"
    raw["temporal"]["reduction"]["length"] = 3
    raw["refresh"]["incremental_strategy"] = "recompute_window"
    raw["refresh"]["window_periods"] = 6
    recipe = load_recipe(_write(tmp_path, raw))
    assert recipe.refresh.incremental_strategy == "recompute_window"


def test_append_period_rejects_cross_period_state_op(tmp_path):
    OPS["_test_stateful_op"] = Op(
        name="_test_stateful_op",
        kind="temporal_reduce",
        period_decomposable=False,
        cross_period_state=True,
        fn=lambda x: x,
    )
    try:
        raw = _load_raw()
        raw["steps"].append({"id": "stateful", "op": "_test_stateful_op", "params": {}})
        with pytest.raises(RecipeError, match="cross_period_state"):
            load_recipe(_write(tmp_path, raw))
    finally:
        del OPS["_test_stateful_op"]


def test_classification_step_requires_pinned_model_hash(tmp_path):
    raw = _load_raw()
    raw["steps"].append({"id": "classify", "op": "temporal_reduce", "kind": "classification", "params": {}})
    with pytest.raises(RecipeError, match="model_hash"):
        load_recipe(_write(tmp_path, raw))


def test_classification_step_with_pinned_model_hash_passes(tmp_path):
    raw = _load_raw()
    raw["steps"].append(
        {
            "id": "classify",
            "op": "temporal_reduce",
            "kind": "classification",
            "params": {"reducer": "mean", "model_hash": "sha256:" + "a" * 64},
        }
    )
    recipe = load_recipe(_write(tmp_path, raw))
    assert recipe.steps[-1].kind == "classification"


def test_rejects_unknown_op(tmp_path):
    raw = _load_raw()
    raw["steps"][0]["op"] = "not_a_real_op"
    with pytest.raises(Exception):
        load_recipe(_write(tmp_path, raw))
