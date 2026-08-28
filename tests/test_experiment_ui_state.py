from experiments.ui_state import (
    WIDGET_STATE_KEYS,
    clear_experiment_state,
    initialize_experiment_state,
    store_completed_experiment,
)


def test_completed_results_use_non_widget_keys():
    state = {}
    initialize_experiment_state(state)
    store_completed_experiment(state, {"random_seed": 42}, {"run_rows": [1]})
    assert state["last_experiment_config"] == {"random_seed": 42}
    assert state["experiment_results"] == {"run_rows": [1]}
    assert state["experiment_completed"] is True
    assert "experiment_config" not in state
    assert "experiment_config_widget" not in state


def test_reset_clears_results_and_widget_values_safely():
    state = {
        "experiment_results": {"run_rows": [1]},
        "last_experiment_config": {"random_seed": 42},
        "experiment_exports": {"run_level.csv": b"data"},
        WIDGET_STATE_KEYS[0]: ["static"],
        "experiment_running": True,
        "experiment_completed": True,
    }
    clear_experiment_state(state)
    assert "experiment_results" not in state
    assert "last_experiment_config" not in state
    assert WIDGET_STATE_KEYS[0] not in state
    assert state["experiment_running"] is False
    assert state["experiment_completed"] is False
