"""Paired feature-flag ablation study for the proposed framework."""
from experiments.experiment_config import ExperimentConfig,VALID_PROFILES
from .ablation_config import ABLATIONS
from .replication_engine import _run
from .statistical_analysis import compare_paired_rows
from .validation_aggregation import summarize
from .validation_export import save_validation_outputs,validation_id

METRICS=("CDRS","final_RWCS","target_reached","trace_completeness","mean_adaptation_latency_ms")

def _figure_data(summary):
    full={row["metric"]:row["mean"] for row in summary if row["ablation"]=="FULL"}
    result=[]
    for row in summary:
        baseline=full[row["metric"]];difference=round(row["mean"]-baseline,6)
        result.append({"configuration":row["ablation"],"metric":row["metric"],
          "mean":row["mean"],"standard_deviation":row["std"],
          "confidence_interval_lower":row["ci95_lower"],
          "confidence_interval_upper":row["ci95_upper"],
          "difference_from_FULL":difference,
          "percentage_difference_from_FULL":round(100*difference/baseline,6) if baseline else None})
    return result

def _report(profiles,episodes,repetitions,seed,summary,statistics):
    result=["# Ablation Study Report","",f"- Configurations: {', '.join(ABLATIONS)}",
      f"- Profiles: {', '.join(profiles)}",f"- Episodes per run: {episodes}",
      f"- Repetitions: {repetitions}",f"- Master seed: {seed}",
      f"- Metrics: {', '.join(METRICS)}","",
      "## Design","",
      "All configurations use profile-and-repetition paired seeds. FULL is the unmodified "
      "Version 3 proposed framework. Each A1–A5 configuration disables exactly one component.",
      "","## Results summary","",
      "| Configuration | Metric | Mean | SD | 95% CI |","|---|---|---:|---:|---:|"]
    for row in summary:
        result.append(f"| {row['ablation']} | {row['metric']} | {row['mean']:.6f} | "
          f"{row['std']:.6f} | [{row['ci95_lower']:.6f}, {row['ci95_upper']:.6f}] |")
    result.extend(["","## Paired statistical comparisons","",
      "| FULL versus | Metric | Test | p | Holm p | Cohen's dz | Rank effect |",
      "|---|---|---|---:|---:|---:|---:|"])
    for row in statistics:
        dz=row["cohens_dz"];rank=row["rank_effect_size"]
        result.append(f"| {row['comparator']} | {row['metric']} | {row['test']} | "
          f"{row['p_value']:.6f} | {row['holm_adjusted_p']:.6f} | "
          f"{dz if dz is not None else 'NA'} | {rank if rank is not None else 'NA'} |")
    result.extend(["","## Limitations","",
      "These are controlled synthetic-participant outcomes. Short runs may be censored, "
      "zero-variance metrics limit effect-size interpretation, and domain risk parameters "
      "require expert validation.","",
      "**Synthetic-validation disclaimer:** These results do not demonstrate human learning, "
      "behavioural transfer, accident reduction, or real-world safety effectiveness.",""])
    return "\n".join(result)

def run_ablation(episodes=30,repetitions=10,seed=42,profiles=None,output_dir=None,progress_callback=None,**_):
    profiles=list(profiles or VALID_PROFILES)
    if episodes<1 or repetitions<1:raise ValueError("episodes and repetitions must be positive")
    rows=[];cycles=[];total=len(ABLATIONS)*len(profiles)*repetitions;done=0
    for ablation_id,setting in ABLATIONS.items():
        for profile in profiles:
            for repetition in range(repetitions):
                paired=ExperimentConfig(random_seed=seed).paired_seed(profile,repetition)
                cr,run,_data=_run("manufacturing",profile,episodes,repetition,paired,features=setting.features())
                run={"ablation":ablation_id,"configuration":setting.features(),**run}
                rows.append(run);cycles.extend({"ablation":ablation_id,**row} for row in cr);done+=1
                if progress_callback:progress_callback(done,total)
    full={(r["profile"],r["repetition"]):r for r in rows if r["ablation"]=="FULL"}
    differences=[]
    for row in rows:
        base=full[(row["profile"],row["repetition"])]
        differences.append({"ablation":row["ablation"],"profile":row["profile"],"repetition":row["repetition"],
          **{f"{metric}_difference_from_FULL":round(float(row[metric])-float(base[metric]),6) for metric in METRICS}})
    summary=summarize(rows,("ablation",),METRICS)
    by_profile=[
      {"configuration":row["ablation"],**{key:value for key,value in row.items() if key!="ablation"}}
      for row in summarize(rows,("ablation","profile"),METRICS)
    ]
    figure_data=_figure_data(summary)
    comparators=[name for name in ABLATIONS if name!="FULL"]
    statistics=[]
    for metric in ("final_RWCS","CDRS","target_reached"):
        statistics.extend(compare_paired_rows(rows,"ablation","FULL",comparators,metric))
    identifier=validation_id("ablation",seed)
    report=_report(profiles,episodes,repetitions,seed,summary,statistics)
    files={"ablation_run_results.csv":rows,"ablation_cycle_results.csv":cycles,
      "ablation_summary.csv":summary,"ablation_differences_from_full.csv":differences,
      "ablation_statistical_comparisons.csv":statistics,
      "ablation_by_profile.csv":by_profile,"ablation_figure_data.csv":figure_data,
      "ablation_report.md":report,
      "ablation_configurations.json":{key:value.features() for key,value in ABLATIONS.items()},
      "ablation_metadata.json":{"validation_id":identifier,"profiles":profiles,
        "episodes":episodes,"repetitions":repetitions,"seed":seed,"metrics":list(METRICS),
        "paired_seed_design":True,"synthetic_outcomes":True}}
    destination=None;downloads={}
    if output_dir is not None:destination,downloads=save_validation_outputs(files,output_dir,identifier)
    return {"validation_id":identifier,"run_results":rows,"cycle_results":cycles,"summary":summary,
      "by_profile":by_profile,"figure_data":figure_data,"report":report,
      "differences":differences,"statistics":statistics,"files":files,"downloads":downloads,
      "output_dir":str(destination) if destination else None}
