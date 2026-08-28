"""CLI for the canonical V15 RACA-PPE synthetic experiment protocol."""
import argparse,sys
from experiments.canonical_config import CANONICAL_METHODS,PROFILES,CanonicalConfig
from experiments.canonical_engine import run_canonical
from experiments.canonical_export import save_canonical

def main(argv=None):
 p=argparse.ArgumentParser(description="Run canonical V15 matched synthetic evaluation (not legacy V3).")
 p.add_argument("--episodes",type=int,default=30);p.add_argument("--repetitions",type=int,default=30);p.add_argument("--seed",type=int,default=42)
 p.add_argument("--methods",nargs="+",choices=CANONICAL_METHODS,default=list(CANONICAL_METHODS));p.add_argument("--profiles",nargs="+",choices=PROFILES,default=list(PROFILES))
 p.add_argument("--output-dir",default="storage/canonical_experiment_results")
 args=p.parse_args(argv)
 try:
  config=CanonicalConfig(methods=args.methods,profiles=args.profiles,episodes=args.episodes,repetitions=args.repetitions,base_seed=args.seed)
  total=len(config.methods)*len(config.profiles)*config.repetitions;print(f"Running {total} canonical V15 runs...")
  result=run_canonical(config,lambda done,total:print(f"Progress {done}/{total}",end="\r"));folder=save_canonical(result,config,args.output_dir)
  print(f"\nCanonical experiment ID: {result['experiment_id']}\nOutput folder: {folder}");return 0
 except Exception as exc:print(f"Canonical experiment failed: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
