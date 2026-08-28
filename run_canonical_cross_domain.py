"""Command-line runner for canonical V15 cross-domain replication."""
import argparse
import sys

from experiments.canonical_config import CanonicalConfig, PROFILES
from experiments.canonical_cross_domain import DOMAINS
from experiments.canonical_cross_domain_engine import run_canonical_cross_domain
from experiments.canonical_cross_domain_export import save_cross_domain


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run canonical V15 cross-domain portability replication.")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--domains", nargs="+", choices=DOMAINS)
    parser.add_argument("--profiles", nargs="+", choices=PROFILES)
    parser.add_argument("--episodes", type=int)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="storage/canonical_cross_domain_results")
    args = parser.parse_args(argv)
    try:
        domains = args.domains or list(DOMAINS); profiles = args.profiles or (["T1", "T2"] if args.smoke else list(PROFILES))
        episodes = args.episodes or (5 if args.smoke else 30); repetitions = args.repetitions or (2 if args.smoke else 30)
        config = CanonicalConfig(methods=["proposed"], profiles=profiles, episodes=episodes, repetitions=repetitions, base_seed=args.seed)
        total = len(domains) * len(profiles) * repetitions
        print(f"Schema gate and {total} canonical cross-domain runs...")
        result = run_canonical_cross_domain(config, domains, lambda done, count: print(f"Progress {done}/{count}", end="\r"))
        folder = save_cross_domain(result, config, domains, args.output_dir)
        print(f"\nCanonical cross-domain ID: {result['experiment_id']}\nOutput folder: {folder}")
        return 0
    except Exception as exc:
        print(f"Canonical cross-domain replication failed: {exc}", file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
