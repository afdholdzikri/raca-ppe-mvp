"""State-key helpers for the Experiment Simulator UI.

This module deliberately has no Streamlit dependency, so its lifecycle behavior
can be tested without instantiating widgets.
"""
from collections.abc import MutableMapping
from typing import Any

RESULT_STATE_KEYS = (
    "last_experiment_config",
    "experiment_results",
    "experiment_exports",
    "experiment_saved_path",
    "experiment_completed",
    "experiment_export_warning",
)

WIDGET_STATE_KEYS = (
    "experiment_methods_widget",
    "experiment_profiles_widget",
    "experiment_episodes_widget",
    "experiment_repetitions_widget",
    "experiment_seed_widget",
    "experiment_target_widget",
    "experiment_learning_rate_widget",
    "experiment_repetition_weight_widget",
    "experiment_save_logs_widget",
    "experiment_save_traces_widget",
    "experiment_profile_filter_widget",
)


def initialize_experiment_state(state: MutableMapping[str, Any]) -> None:
    state.setdefault("experiment_running", False)
    state.setdefault("experiment_completed", False)


def store_completed_experiment(
    state: MutableMapping[str, Any],
    config_snapshot: dict[str, Any],
    results: dict[str, Any],
) -> None:
    """Commit successful scientific results before optional export work."""
    state["last_experiment_config"] = dict(config_snapshot)
    state["experiment_results"] = results
    state["experiment_completed"] = True
    state["experiment_export_warning"] = None


def clear_experiment_state(
    state: MutableMapping[str, Any],
    *,
    clear_widget_values: bool = True,
) -> None:
    """Clear result state and, from a callback, optionally clear widget values."""
    for key in RESULT_STATE_KEYS:
        state.pop(key, None)
    if clear_widget_values:
        for key in WIDGET_STATE_KEYS:
            state.pop(key, None)
    state["experiment_running"] = False
    state["experiment_completed"] = False
