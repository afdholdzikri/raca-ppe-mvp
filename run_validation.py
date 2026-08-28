"""Command-line entry point for RACA PPE scientific validation.

The runner intentionally contains no scientific formulas.  It delegates the
prerequisite diagnostic to the existing experiment engine and delegates other
Version 4 modes to their corresponding modules when those modules are present.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

from experiments.experiment_config import ExperimentConfig, VALID_METHODS, VALID_PROFILES
from experiments.export_manager import build_exports, save_exports
from experiments.simulation_engine import run_batch_experiments


MODES = ("prerequisite", "ablation", "sensitivity", "trace-audit", "replication", "all")
class ValidationFailure(RuntimeError):
    """A readable validation failure suitable for CLI output."""


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RACA PPE Version 4 scientific validation workflows."
    )
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--episodes", type=positive_integer, default=30)
    parser.add_argument("--repetitions", type=positive_integer, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--profiles", nargs="+", choices=VALID_PROFILES, default=list(VALID_PROFILES)
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("storage") / "validation_results"
    )
    parser.add_argument("--parameter", help="Sensitivity parameter name.")
    parser.add_argument(
        "--values", nargs="+", type=float, help="Sensitivity parameter values."
    )
    parser.add_argument(
        "--domains", nargs="+", help="Domain identifiers for replication."
    )
    return parser


def validate_mode_arguments(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.mode == "sensitivity":
        if not args.parameter or not args.values:
            parser.error("sensitivity mode requires --parameter and --values")
        if not all(math.isfinite(value) for value in args.values):
            parser.error("--values must contain only finite numbers")
    elif args.mode != "all" and (args.parameter is not None or args.values is not None):
        parser.error("--parameter and --values are only valid in sensitivity mode")

    if args.mode == "replication" and not args.domains:
        parser.error("replication mode requires --domains")
    if args.mode not in ("replication","all") and args.domains is not None:
        parser.error("--domains is only valid in replication mode")


def _maximum_scenario_streak(episode_rows: list[dict[str, Any]]) -> int:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in episode_rows:
        grouped.setdefault(row["run_id"], []).append(row)
    maximum = 0
    for rows in grouped.values():
        previous = None
        streak = 0
        for row in sorted(rows, key=lambda item: item["episode"]):
            streak = streak + 1 if row["scenario_id"] == previous else 1
            previous = row["scenario_id"]
            maximum = max(maximum, streak)
    return maximum


def prerequisite_status(result: dict[str, Any], config: ExperimentConfig) -> dict[str, Any]:
    """Evaluate structural prerequisites using existing experiment outputs."""
    episode_rows = result["episode_rows"]
    run_rows = result["run_rows"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in episode_rows:
        grouped.setdefault(row["run_id"], []).append(row)

    competence_persisted = all(
        rows[index]["competence_after"] == rows[index + 1]["competence_before"]
        for rows in grouped.values()
        for index in range(len(rows) - 1)
    )
    competence_bounded = all(
        all(0.0 <= score <= 1.0 for score in row["competence_after"].values())
        for row in episode_rows
    )
    difficulty_bounded = all(
        config.minimum_difficulty <= row["next_difficulty"] <= config.maximum_difficulty
        for row in episode_rows
    )
    scenario_efficiency_valid = all(
        row["SE"]
        == (
            row["episode_target_reached"]
            if row["target_reached"]
            else config.episodes_per_run + 1
        )
        for row in run_rows
    )
    adaptation_relevance_nontrivial = len({row["AR"] for row in run_rows}) > 1
    proposed_rows = [
        row for row in episode_rows if row.get("method", "proposed") == "proposed"
    ]
    proposed_maximum_streak = _maximum_scenario_streak(proposed_rows)
    remediation_bounded = proposed_maximum_streak <= 2

    checks = {
        "competence_persisted": competence_persisted,
        "competence_bounded": competence_bounded,
        "difficulty_bounded": difficulty_bounded,
        "scenario_efficiency_valid": scenario_efficiency_valid,
        "adaptation_relevance_nontrivial": adaptation_relevance_nontrivial,
        "remediation_bounded": remediation_bounded,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "runs": len(run_rows),
        "episodes": len(episode_rows),
        "targets_reached": sum(bool(row["target_reached"]) for row in run_rows),
        "maximum_scenario_streak": proposed_maximum_streak,
        "adaptation_relevance_values": sorted({row["AR"] for row in run_rows}),
    }


def run_prerequisite(args: argparse.Namespace) -> int:
    config = ExperimentConfig(
        methods=list(VALID_METHODS),
        trainee_profiles=list(args.profiles),
        episodes_per_run=args.episodes,
        repetitions=args.repetitions,
        random_seed=args.seed,
    )
    total = len(config.methods) * len(config.trainee_profiles) * config.repetitions
    print(f"Running prerequisite diagnostic: {total} runs")

    last_percent = -1

    def progress(done: int, count: int) -> None:
        nonlocal last_percent
        percent = int(done * 100 / count)
        if percent == 100 or percent >= last_percent + 10:
            print(f"Progress: {done}/{count} ({percent}%)")
            last_percent = percent

    result = run_batch_experiments(config, progress)
    status = prerequisite_status(result, config)
    print(f"Prerequisite status: {status['status']}")
    for name, passed in status["checks"].items():
        print(f"  {'PASS' if passed else 'FAIL'}: {name}")
    print(
        f"Runs: {status['runs']}; episodes: {status['episodes']}; "
        f"targets reached: {status['targets_reached']}"
    )

    files = build_exports(result, config, Path(__file__).parent / "data")
    files["prerequisite_status.json"] = json.dumps(
        status, indent=2, sort_keys=True
    ).encode("utf-8")
    destination = save_exports(files, result["experiment_id"], args.output_dir)
    if destination is None:
        raise ValidationFailure(
            f"prerequisite completed, but outputs could not be saved under {args.output_dir}"
        )
    print(f"Outputs: {destination}")
    return 0 if status["status"] == "PASS" else 2


def run_version4_mode(mode: str, args: argparse.Namespace) -> int:
    print(f"Running {mode} validation")
    progress=lambda done,total: print(f"Progress: {done}/{total}") if done==total or done%max(1,total//10)==0 else None
    if mode=="ablation":
        from experiments.ablation_engine import run_ablation
        result=run_ablation(args.episodes,args.repetitions,args.seed,args.profiles,args.output_dir,progress)
    elif mode=="sensitivity":
        from experiments.sensitivity_engine import run_sensitivity
        result=run_sensitivity(args.parameter,args.values,args.episodes,args.repetitions,args.seed,args.profiles,args.output_dir,progress)
    elif mode=="replication":
        from experiments.replication_engine import run_cross_domain_replication
        result=run_cross_domain_replication(args.domains,args.profiles,args.episodes,args.repetitions,args.seed,args.output_dir,progress)
    elif mode=="trace-audit":
        from experiments.replication_engine import run_cross_domain_replication
        from experiments.trace_audit import run_trace_audit
        sample=run_cross_domain_replication(["manufacturing"],args.profiles[:1],
          min(args.episodes,5),1,args.seed,None)
        result=run_trace_audit(sample["cycle_results"],args.seed,args.output_dir)
    else:raise ValidationFailure(f"unsupported mode {mode}")
    print(f"{mode} status: PASS")
    if result.get("output_dir"):print(f"Outputs: {result['output_dir']}")
    return 0


def execute(args: argparse.Namespace) -> int:
    if args.mode == "prerequisite":
        return run_prerequisite(args)
    if args.mode == "all":
        code = run_prerequisite(args)
        if code:
            return code
        for mode in ("ablation","trace-audit","replication"):
            if mode=="replication" and args.domains is None:
                args.domains=["manufacturing","chemical_laboratory","construction"]
            code=run_version4_mode(mode,args)
            if code:
                return code
        from experiments.sensitivity_config import SENSITIVITY_GRIDS
        original_parameter,original_values=args.parameter,args.values
        for parameter in SENSITIVITY_GRIDS:
            args.parameter=parameter;args.values=None
            code=run_version4_mode("sensitivity",args)
            if code:return code
        args.parameter,args.values=original_parameter,original_values
        return 0
    return run_version4_mode(args.mode, args)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_mode_arguments(args, parser)
    try:
        return execute(args)
    except (ValidationFailure, ValueError, OSError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Validation interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
