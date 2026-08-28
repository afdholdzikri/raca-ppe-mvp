"""In-memory and failure-tolerant local experiment exports."""
import hashlib,io,json,platform,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from .experiment_metrics import RUN_METRICS

def configuration_hash(config):
    value=config.to_dict() if hasattr(config,"to_dict") else config
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:10]
def json_bytes(value): return json.dumps(value,indent=2,sort_keys=True,default=str).encode()
def csv_bytes(rows,columns=None): return pd.DataFrame(rows,columns=columns if not rows else None).to_csv(index=False).encode()
def jsonl_bytes(rows): return ("\n".join(json.dumps(x,sort_keys=True,default=str) for x in rows)+("\n" if rows else "")).encode()

def dataset_hashes(data_dir):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(data_dir).glob("*.json"))}
def git_commit():
    try: return subprocess.check_output(["git","rev-parse","HEAD"],text=True,stderr=subprocess.DEVNULL,timeout=2).strip()
    except Exception: return None
def metadata(result,config,data_dir):
    return {"experiment_id":result["experiment_id"],"execution_timestamp":datetime.now(timezone.utc).isoformat(),
      "software_version":"3.0.0-prototype","python_version":sys.version,"platform":platform.platform(),
      "methods":config.methods,"profiles":config.trainee_profiles,"episodes":config.episodes_per_run,
      "repetitions":config.repetitions,"master_seed":config.random_seed,
      "configuration_hash":configuration_hash(config),"dataset_file_hashes":dataset_hashes(data_dir),
      "git_commit_hash":git_commit(),"metric_definitions":list(RUN_METRICS),
      "stopping_condition":"All high-risk competencies >= target and mean competence >= target-0.05",
      "warnings":["Synthetic-participant simulation only; not evidence of human learning or accident reduction.",
                  "CI95 uses a 1.96 normal approximation."]}
def report_markdown(result):
    return f"# Experiment {result['experiment_id']}\\n\\nComputational proof-of-work using synthetic participants.\\n\\nRuns: {len(result['run_rows'])}\\nEpisodes: {len(result['episode_rows'])}\\n"
def build_exports(result,config,data_dir):
    meta=metadata(result,config,data_dir)
    files={"configuration.json":json_bytes(config.to_dict()),"trainee_profiles.json":(Path(data_dir)/"trainee_profiles.json").read_bytes(),
      "episode_level.csv":csv_bytes(result["episode_rows"],["experiment_id","run_id","method","trainee_profile","episode"]),
      "run_level.csv":csv_bytes(result["run_rows"],["experiment_id","run_id","method","trainee_profile"]),
      "aggregated_summary.csv":csv_bytes(result.get("aggregated_all",result["aggregated"]),["aggregation_level","metric","count","mean"]),
      "figure5_data.csv":csv_bytes(result["figure5_data"],["method","metric","count","mean","std"]),
      "figure6_data.csv":csv_bytes(result["figure6_data"],["method","episode","mean_RWCS","std_RWCS","ci95_lower","ci95_upper","count"]),
      "decision_traces.jsonl":jsonl_bytes(result["decision_traces"]),
      "metadata.json":json_bytes(meta),"REPORT.md":report_markdown(result).encode()}
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for name,value in files.items(): z.writestr(name,value)
    files["complete_experiment.zip"]=archive.getvalue()
    return files
def save_exports(files,experiment_id,output_root=Path("storage")/"experiment_results"):
    try:
        destination=Path(output_root)/experiment_id; destination.mkdir(parents=True,exist_ok=False)
        for name,value in files.items(): (destination/name).write_bytes(value)
        return destination
    except OSError: return None
