import json,zipfile,io
import pandas as pd
from pathlib import Path
from experiments.experiment_config import ExperimentConfig
from experiments.export_manager import *
from experiments.simulation_engine import run_batch_experiments

def test_hash_stability_and_serialization():
 c=ExperimentConfig(methods=["static"],trainee_profiles=["T1"],episodes_per_run=1,repetitions=1)
 assert configuration_hash(c)==configuration_hash(c)
 assert json.loads(json_bytes({"x":1}))["x"]==1 and b"x" in csv_bytes([{"x":1}]) and jsonl_bytes([{"x":1}])
def test_exports_metadata_zip_and_save(tmp_path):
 c=ExperimentConfig(methods=["static"],trainee_profiles=["T1"],episodes_per_run=1,repetitions=1)
 r=run_batch_experiments(c); files=build_exports(r,c,Path(__file__).parent.parent/"data")
 meta=json.loads(files["metadata.json"]); assert {"experiment_id","configuration_hash","dataset_file_hashes","master_seed"}<=meta.keys()
 assert "episode_level.csv" in zipfile.ZipFile(io.BytesIO(files["complete_experiment.zip"])).namelist()
 assert save_exports(files,r["experiment_id"],tmp_path)
def test_local_failure_safe(tmp_path):
 blocker=tmp_path/"file"; blocker.write_text("x")
 assert save_exports({"x":b"x"},"id",blocker) is None
def test_empty_csv_has_readable_headers():
 assert list(pd.read_csv(io.BytesIO(csv_bytes([],["a","b"]))).columns)==["a","b"]
