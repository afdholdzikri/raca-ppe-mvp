"""One-factor-at-a-time sensitivity analysis."""
from experiments.experiment_config import ExperimentConfig,VALID_PROFILES
from .replication_engine import _run
from .sensitivity_config import BASE_VALUES,SENSITIVITY_GRIDS,ofat_configuration
from .validation_aggregation import summarize
from .validation_export import save_validation_outputs,validation_id

METRICS=("final_RWCS","CER","CDRS","target_reached")

def normalized_variation(values):
    mean=sum(values)/len(values) if values else 0
    return round((max(values)-min(values))/abs(mean),6) if mean else 0.0

def run_sensitivity(parameter=None,values=None,episodes=30,repetitions=10,seed=42,
                    profiles=None,output_dir=None,progress_callback=None,**_):
    if parameter not in SENSITIVITY_GRIDS:raise ValueError(f"parameter must be one of {', '.join(SENSITIVITY_GRIDS)}")
    values=[float(v) for v in (values or SENSITIVITY_GRIDS[parameter])]
    profiles=list(profiles or VALID_PROFILES);rows=[];total=len(values)*len(profiles)*repetitions;done=0
    for value in values:
        config=ofat_configuration(parameter,value)
        for profile in profiles:
            for repetition in range(repetitions):
                paired=ExperimentConfig(random_seed=seed).paired_seed(profile,repetition)
                _cycles,run,_data=_run("manufacturing",profile,episodes,repetition,paired,**config)
                rows.append({"parameter":parameter,"value":value,"configuration":config,**run});done+=1
                if progress_callback:progress_callback(done,total)
    summary=summarize(rows,("parameter","value"),METRICS);variation=[]
    for metric in METRICS:
        means=[row["mean"] for row in summary if row["metric"]==metric]
        nv=normalized_variation(means)
        variation.append({"parameter":parameter,"metric":metric,"normalized_variation":nv,
          "SOR":round(1/(1+nv),6)})
    identifier=validation_id("sensitivity",seed)
    files={"sensitivity_run_results.csv":rows,"sensitivity_summary.csv":summary,
      "sensitivity_variation.csv":variation,"sensitivity_configurations.json":{
      "base_values":BASE_VALUES,"parameter":parameter,"values":values},
      "sensitivity_metadata.json":{"validation_id":identifier,"seed":seed,"synthetic_outcomes":True}}
    destination=None;downloads={}
    if output_dir is not None:destination,downloads=save_validation_outputs(files,output_dir,identifier)
    return {"validation_id":identifier,"run_results":rows,"summary":summary,"variation":variation,
      "files":files,"downloads":downloads,"output_dir":str(destination) if destination else None}
