"""Command-line runner for Version 3 experiments."""
import argparse,sys
from pathlib import Path
from experiments.experiment_config import ExperimentConfig,VALID_METHODS,VALID_PROFILES
from experiments.simulation_engine import run_batch_experiments
from experiments.export_manager import build_exports,save_exports

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--episodes",type=int,default=30); p.add_argument("--repetitions",type=int,default=30)
    p.add_argument("--seed",type=int,default=42); p.add_argument("--methods",nargs="+",choices=VALID_METHODS,default=list(VALID_METHODS))
    p.add_argument("--profiles",nargs="+",choices=VALID_PROFILES,default=list(VALID_PROFILES)); p.add_argument("--output-dir",default="storage/experiment_results")
    a=p.parse_args(argv)
    try:
        c=ExperimentConfig(methods=a.methods,trainee_profiles=a.profiles,episodes_per_run=a.episodes,repetitions=a.repetitions,random_seed=a.seed)
        print(f"Running {len(c.methods)*len(c.trainee_profiles)*c.repetitions} runs...")
        r=run_batch_experiments(c,lambda done,total: print(f"Progress {done}/{total}",end="\\r"))
        files=build_exports(r,c,Path(__file__).parent/"data"); dest=save_exports(files,r["experiment_id"],a.output_dir)
        if dest is None: raise RuntimeError("could not save experiment outputs")
        print(f"\\nExperiment ID: {r['experiment_id']}\\nOutput folder: {dest}")
        for row in r["overall_table"]: print(row)
        return 0
    except Exception as exc: print(f"Experiment failed: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
