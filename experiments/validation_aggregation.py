"""Aggregation helpers for Version 4 validation outputs."""
from __future__ import annotations
import math
from collections import defaultdict

def safe_rate(numerator,denominator):return round(numerator/denominator,6) if denominator else 0.0

def summarize(rows,group_fields,metrics):
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[field] for field in group_fields)].append(row)
    result=[]
    for key,items in sorted(groups.items()):
        prefix=dict(zip(group_fields,key))
        for metric in metrics:
            values=[float(item[metric]) for item in items];n=len(values);mean=sum(values)/n
            variance=sum((x-mean)**2 for x in values)/(n-1) if n>1 else 0.0
            se=math.sqrt(variance/n) if n else 0.0
            result.append({**prefix,"metric":metric,"count":n,"mean":round(mean,6),
              "std":round(math.sqrt(variance),6),"ci95_lower":round(mean-1.96*se,6),
              "ci95_upper":round(mean+1.96*se,6)})
    return result

def replication_summary(run_rows):
    return summarize(run_rows,("domain",),("CDRS","trace_completeness","target_reached",
      "scenario_validation_success","rule_execution_success","mean_adaptation_latency_ms"))
