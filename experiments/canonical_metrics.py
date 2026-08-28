"""Canonical V15 latent outcomes, post-test, operations, and paired reporting."""
from __future__ import annotations
from statistics import mean,median
import numpy as np

HIGHER_BETTER=("CCG_star","RWCS_star","TAR","AR","DC","TC","CDRS")
LOWER_BETTER=("CER","CMR","SOR","episodes_to_target")

def latent_outcomes(initial,final,definitions,weights,target):
    critical=[c for c,d in definitions.items() if d.high_risk_related]
    ccg=mean(final[c]-initial[c] for c in critical) if critical else 0
    denom=sum(weights.values()); rwcs=sum(final[c]*weights[c] for c in final)/denom if denom else mean(final.values())
    tar=sum(final[c]>=target for c in final)/len(final)
    return {"CCG_star":round(ccg,6),"RWCS_star":round(rwcs,6),"TAR":round(tar,6)}

def posttest_metrics(rows,critical_threshold=.75):
    """Aggregate one canonical run's fixed post-test records only."""
    run_ids={r.get("canonical_run_id") for r in rows if r.get("canonical_run_id") is not None}
    methods={r.get("method") for r in rows if r.get("method") is not None}
    if len(run_ids)>1 or len(methods)>1:
        raise ValueError("post-test metrics must be calculated from one canonical run")
    critical=[r for r in rows if r["scenario_risk"]>=critical_threshold]
    cer=sum(not r["correct"] for r in critical)/len(critical) if critical else 0
    required=sum(len(r["required_ppe"]) for r in rows); missing=sum(len(r["missing_ppe"]) for r in rows)
    return {"CER":round(cer,6),"CMR":round(missing/required,6) if required else 0}

def scenario_oscillation_rate(ids):
    if len(ids)<3:return 0.0
    oscillations=sum(ids[i]==ids[i-2] and ids[i]!=ids[i-1] for i in range(2,len(ids)))
    return round(oscillations/(len(ids)-2),6)

def paired_differences(run_rows):
    proposed={(r["profile"],r["repetition"]):r for r in run_rows if r["method"]=="proposed"}; output=[]
    for comparator in sorted({r["method"] for r in run_rows}-{ "proposed"}):
        privileged=comparator=="oracle"
        comp={(r["profile"],r["repetition"]):r for r in run_rows if r["method"]==comparator}
        for metric in (*HIGHER_BETTER,*LOWER_BETTER):
            values=[]
            for key in sorted(proposed.keys()&comp.keys()):
                p,c=proposed[key][metric],comp[key][metric]
                values.append((p-c) if metric in HIGHER_BETTER else (c-p))
            if not values:continue
            low,high=np.quantile(values,[.025,.975])
            output.append({"comparator":comparator,"privileged_reference":privileged,"metric":metric,
              "orientation":"positive = Proposed is better","mean_paired_difference":round(mean(values),6),
              "median_paired_difference":round(median(values),6),"mc95_lower":round(float(low),6),
              "mc95_upper":round(float(high),6),"win_rate":round(sum(v>0 for v in values)/len(values),6),"matched_pairs":len(values)})
    return output
