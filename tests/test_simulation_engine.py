import sys
from experiments.experiment_config import ExperimentConfig
from experiments.simulation_engine import EXPERIMENT_TRACE_FIELDS,RUN_REQUIRED_FIELDS,run_single_experiment,run_batch_experiments

def config(seed=42):
 return ExperimentConfig(methods=["static","score_adaptive","competence_adaptive","proposed"],
  trainee_profiles=["T1","T2"],episodes_per_run=5,repetitions=2,random_seed=seed)
def strip_nondeterministic(result):
 return [{k:v for k,v in r.items() if k not in {"adaptation_latency_ms","experiment_id"}}
  for r in result["episode_rows"]]
def test_single_run_complete_and_fields():
 c=config(); r=run_single_experiment("proposed","T1",c,42)
 assert 1<=len(r["episode_rows"])<=5 and EXPERIMENT_TRACE_FIELDS<=r["episode_rows"][0].keys()
 assert RUN_REQUIRED_FIELDS<=r["run_row"].keys()
 assert r["run_row"]["episodes_completed"]<=5
def test_batch_shape_and_equal_configuration():
 r=run_batch_experiments(config()); assert len(r["run_rows"])==16
 assert {x["method"] for x in r["run_rows"]}=={"static","score_adaptive","competence_adaptive","proposed"}
def test_experiment_ids_are_unique():
 c=config(); assert run_batch_experiments(c)["experiment_id"]!=run_batch_experiments(c)["experiment_id"]
def test_batch_contains_all_aggregation_levels():
 r=run_batch_experiments(config())
 assert set(x["aggregation_level"] for x in r["aggregated_all"])=={"method","trainee_profile","method_x_profile"}
def test_reproducible_and_seed_variation():
 a=run_batch_experiments(config(42)); b=run_batch_experiments(config(42)); c=run_batch_experiments(config(43))
 assert strip_nondeterministic(a)==strip_nondeterministic(b)
 assert strip_nondeterministic(a)!=strip_nondeterministic(c)
def test_experiment_core_has_no_streamlit_import():
 assert not any(name=="streamlit" or name.startswith("streamlit.") for name in sys.modules if name.startswith("experiments"))
