from experiments.aggregation import aggregate_all,aggregate_results,figure6_data
from experiments.experiment_metrics import RUN_METRICS

def rows():
 return [dict(method="static",trainee_profile="T1",target_reached=False,**{m:v for m in RUN_METRICS})
  for v in (1.0,3.0)]
def test_mean_std_ci_and_grouping():
 a=aggregate_results(rows()); ccg=a[a.metric=="CCG"].iloc[0]
 assert ccg["mean"]==2 and ccg["std"]>0 and ccg["ci95_lower"]<2<ccg["ci95_upper"]
 assert len(aggregate_results(rows(),("method","trainee_profile")))>0
def test_empty_and_one_row():
 assert aggregate_results([]).empty
 one=aggregate_results(rows()[:1]); assert (one["std"]==0).all()
def test_figure6_locf():
 e=[{"run_id":"r","method":"static","episode":1,"current_RWCS":.4}]
 assert len(figure6_data(e,3))==3
def test_all_required_aggregation_levels():
 assert set(aggregate_all(rows()).aggregation_level)=={"method","trainee_profile","method_x_profile"}
