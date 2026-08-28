"""CLI for the corrected canonical V15 ablation protocol."""
import argparse,sys
from experiments.canonical_config import CanonicalConfig,PROFILES
from experiments.canonical_ablation import ABLATIONS
from experiments.canonical_ablation_engine import run_canonical_ablation
from experiments.canonical_ablation_export import save_canonical_ablation

def main(argv=None):
 p=argparse.ArgumentParser(description="Run canonical V15 ablation (not legacy V4).")
 p.add_argument("--episodes",type=int,default=30);p.add_argument("--repetitions",type=int,default=30);p.add_argument("--seed",type=int,default=42)
 p.add_argument("--profiles",nargs="+",choices=PROFILES,default=list(PROFILES));p.add_argument("--output-dir",default="storage/canonical_ablation_results")
 a=p.parse_args(argv)
 try:
  cfg=CanonicalConfig(methods=["proposed"],profiles=a.profiles,episodes=a.episodes,repetitions=a.repetitions,base_seed=a.seed)
  total=len(ABLATIONS)*len(cfg.profiles)*cfg.repetitions;print(f"Running {total} canonical V15 ablation runs...")
  result=run_canonical_ablation(cfg,lambda done,total:print(f"Progress {done}/{total}",end="\r"));folder=save_canonical_ablation(result,cfg,a.output_dir)
  print(f"\nCanonical ablation ID: {result['experiment_id']}\nOutput folder: {folder}");return 0
 except Exception as exc:print(f"Canonical ablation failed: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
