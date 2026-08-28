import argparse

import pytest

import run_validation
from experiments.experiment_config import ExperimentConfig


def test_parser_accepts_exact_prerequisite_command():
    parser = run_validation.build_parser()
    args = parser.parse_args(["--mode", "prerequisite", "--seed", "42"])
    run_validation.validate_mode_arguments(args, parser)
    assert args.mode == "prerequisite"
    assert args.seed == 42


def test_positive_integer_rejects_zero():
    with pytest.raises(argparse.ArgumentTypeError):
        run_validation.positive_integer("0")


def test_version4_modes_are_registered():
    assert {"ablation","sensitivity","trace-audit","replication"} <= set(run_validation.MODES)


def test_prerequisite_status_accepts_consistent_rows():
    config = ExperimentConfig(
        methods=["proposed"],
        trainee_profiles=["T1"],
        episodes_per_run=2,
        repetitions=1,
    )
    competence = {"c": 0.4}
    episodes = [
        {
            "run_id": "run",
            "episode": 1,
            "scenario_id": "S1",
            "competence_before": competence,
            "competence_after": competence,
            "next_difficulty": 1,
        },
        {
            "run_id": "run",
            "episode": 2,
            "scenario_id": "S1",
            "competence_before": competence,
            "competence_after": competence,
            "next_difficulty": 3,
        },
    ]
    runs = [
        {
            "SE": 3,
            "episode_target_reached": 3,
            "target_reached": False,
            "AR": 0.0,
        },
        {
            "SE": 3,
            "episode_target_reached": 3,
            "target_reached": False,
            "AR": 1.0,
        },
    ]
    status = run_validation.prerequisite_status(
        {"episode_rows": episodes, "run_rows": runs}, config
    )
    assert status["status"] == "PASS"
