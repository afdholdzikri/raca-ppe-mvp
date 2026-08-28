"""CLI for canonical V15 sensitivity/robustness, separate from legacy validation."""
import argparse,sys
from core.data_loader import load_all_data
from experiments.canonical_config import CanonicalConfig,PROFILES
from experiments.canonical_sensitivity import final_conditions,smoke_conditions
from experiments.canonical_sensitivity_engine import run_canonical_sensitivity
from experiments.canonical_sensitivity_export import save_canonical_sensitivity
def main(argv=None):
 p=argparse.ArgumentParser(description="Run canonical V15 OFAT sensitivity and robustness.");p.add_argument("--smoke",action="store_true");p.add_argument("--episodes",type=int);p.add_argument("--repetitions",type=int);p.add_argument("--seed",type=int,default=42);p.add_argument("--profiles",nargs="+",choices=PROFILES);p.add_argument("--output-dir",default="storage/canonical_sensitivity_results");a=p.parse_args(argv)
 try:
  episodes=a.episodes or (5 if a.smoke else 30);repetitions=a.repetitions or (2 if a.smoke else 30);profiles=a.profiles or (["T1","T2"] if a.smoke else list(PROFILES));conditions=smoke_conditions() if a.smoke else final_conditions();cfg=CanonicalConfig(methods=["proposed"],profiles=profiles,episodes=episodes,repetitions=repetitions,base_seed=a.seed)
  total=sum(len(c.methods) for c in conditions)*len(profiles)*repetitions;print(f"Running {total} canonical V15 sensitivity runs...");result=run_canonical_sensitivity(cfg,conditions,lambda d,t:print(f"Progress {d}/{t}",end="\r"));folder=save_canonical_sensitivity(result,cfg,conditions,load_all_data()["competencies"],a.output_dir);print(f"\nCanonical sensitivity ID: {result['experiment_id']}\nOutput folder: {folder}");return 0
 except Exception as exc:print(f"Canonical sensitivity failed: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
