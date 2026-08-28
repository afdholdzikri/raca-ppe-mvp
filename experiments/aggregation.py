"""Normal-approximation summaries (CI95 = mean ± 1.96 SE)."""
import math
import pandas as pd
from .experiment_metrics import RUN_METRICS

def aggregate_results(run_rows,group_by=("method",)):
    columns=list(group_by)+["metric","count","mean","std","median","min","max","standard_error","ci95_lower","ci95_upper"]
    if not run_rows: return pd.DataFrame(columns=columns)
    df=pd.DataFrame(run_rows); result=[]
    grouped=df.groupby(list(group_by),dropna=False)
    for keys,group in grouped:
        if not isinstance(keys,tuple): keys=(keys,)
        prefix=dict(zip(group_by,keys))
        for metric in RUN_METRICS:
            values=group[metric].astype(float); count=len(values); mean=values.mean()
            std=values.std(ddof=1) if count>1 else 0.0; se=std/math.sqrt(count) if count else 0
            result.append({**prefix,"metric":metric,"count":count,"mean":mean,"std":std,
              "median":values.median(),"min":values.min(),"max":values.max(),
              "standard_error":se,"ci95_lower":mean-1.96*se,"ci95_upper":mean+1.96*se})
    return pd.DataFrame(result,columns=columns)

def aggregate_all(run_rows):
    """Return method, profile, and method×profile summaries in one table."""
    frames=[]
    for level,groups in (
        ("method",("method",)),
        ("trainee_profile",("trainee_profile",)),
        ("method_x_profile",("method","trainee_profile")),
    ):
        frame=aggregate_results(run_rows,groups)
        frame.insert(0,"aggregation_level",level)
        frames.append(frame)
    return pd.concat(frames,ignore_index=True,sort=False) if frames else pd.DataFrame()

def overall_performance_table(run_rows):
    labels={"static":"Static Baseline","score_adaptive":"Score-Based Adaptive",
      "competence_adaptive":"Competence-Adaptive","proposed":"Proposed Framework"}
    agg=aggregate_results(run_rows); rates=pd.DataFrame(run_rows).groupby("method")["target_reached"].mean()
    rows=[]
    for method in sorted(set(r["method"] for r in run_rows)):
        subset=agg[agg.method==method].set_index("metric")
        fmt=lambda m:f"{subset.loc[m,'mean']:.4f} ± {subset.loc[m,'std']:.4f}"
        rows.append({"Method":labels[method],"CCG mean ± SD":fmt("CCG"),"RWCS mean ± SD":fmt("RWCS"),
          "CER mean ± SD":fmt("CER"),"AR mean ± SD":fmt("AR"),"SE mean ± SD":fmt("SE"),
          "Adaptation Latency mean ± SD":fmt("mean_adaptation_latency_ms"),
          "Target Achievement Rate":rates[method]})
    return pd.DataFrame(rows)

def figure5_data(run_rows): return aggregate_results(run_rows)[lambda x:x.metric.isin(["CCG","RWCS","CER","AR","SE"])]

def figure6_data(episode_rows,max_episode):
    if not episode_rows: return pd.DataFrame(columns=["method","episode","mean_RWCS","std_RWCS","ci95_lower","ci95_upper","count"])
    df=pd.DataFrame(episode_rows); runs=df[["run_id","method"]].drop_duplicates(); expanded=[]
    for _,run in runs.iterrows():
        part=df[df.run_id==run.run_id].sort_values("episode"); last=None
        for episode in range(1,max_episode+1):
            row=part[part.episode==episode]
            if not row.empty: last=float(row.iloc[0]["current_RWCS"])
            if last is not None: expanded.append({"method":run.method,"run_id":run.run_id,"episode":episode,"RWCS":last})
    values=pd.DataFrame(expanded); result=[]
    for (method,episode),g in values.groupby(["method","episode"]):
        n=len(g); mean=g.RWCS.mean(); std=g.RWCS.std(ddof=1) if n>1 else 0; se=std/math.sqrt(n)
        result.append({"method":method,"episode":episode,"mean_RWCS":mean,"std_RWCS":std,
          "ci95_lower":mean-1.96*se,"ci95_upper":mean+1.96*se,"count":n})
    return pd.DataFrame(result)
