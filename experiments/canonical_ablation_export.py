"""Canonical-only V15 ablation export and paired reporting."""
from __future__ import annotations
import csv,io,json
from pathlib import Path
from statistics import mean,median,pstdev
import numpy as np
from .canonical_ablation import ABLATIONS,manifest

HIGHER=("CCG_star","RWCS_star","TAR","AR","DC","TC")
LOWER=("CER","CMR","SOR","episodes_to_target","adaptation_latency_ms")

def _cell(v):return json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v
def _csv(rows):
 if not rows:return b""
 fields=[]
 for row in rows:
  for key in row:
   if key not in fields:fields.append(key)
 s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows({k:_cell(v) for k,v in r.items()} for r in rows);return s.getvalue().encode()
def _summary(rows,groups):
 out=[];grouped={}
 for row in rows:grouped.setdefault(tuple(row[g] for g in groups),[]).append(row)
 for key,values in sorted(grouped.items()):
  for metric in (*HIGHER,*LOWER):
   nums=[float(r[metric]) for r in values];out.append({**dict(zip(groups,key)),"metric":metric,"count":len(nums),"mean":round(mean(nums),6),"std":round(pstdev(nums),6)})
 return out
def paired(rows,by_profile=False):
 base={(r["profile"],r["repetition"]):r for r in rows if r["configuration"]=="complete_framework"};out=[]
 for variant in ABLATIONS:
  if variant=="complete_framework":continue
  comp={(r["profile"],r["repetition"]):r for r in rows if r["configuration"]==variant}
  profiles=sorted({k[0] for k in base}) if by_profile else [None]
  for profile in profiles:
   keys=sorted(k for k in base.keys()&comp.keys() if profile is None or k[0]==profile)
   for metric in (*HIGHER,*LOWER):
    vals=[float(base[k][metric])-float(comp[k][metric]) if metric in HIGHER else float(comp[k][metric])-float(base[k][metric]) for k in keys]
    lo,hi=np.quantile(vals,[.025,.975]);out.append({"configuration":variant,**({"profile":profile} if by_profile else {}),"metric":metric,
      "orientation":"positive = Complete Framework is better","mean_paired_difference":round(mean(vals),6),
      "median_paired_difference":round(median(vals),6),"mc95_lower":round(float(lo),6),"mc95_upper":round(float(hi),6),
      "win_rate":round(sum(v>0 for v in vals)/len(vals),6),"matched_pairs":len(vals)})
 return out

def save_canonical_ablation(result,config,output_root):
 folder=Path(output_root)/result["experiment_id"];folder.mkdir(parents=True,exist_ok=False)
 summary=_summary(result["run_rows"],["configuration"]);profile_summary=_summary(result["run_rows"],["configuration","profile"])
 paired_rows=paired(result["run_rows"]);profile_pairs=paired(result["run_rows"],True)
 target=[{k:r[k] for k in ("canonical_ablation_run_id","configuration","profile","repetition","repetition_seed","target_reached","episodes_to_target","censored","TAR")} for r in result["run_rows"]]
 fidelity=[{k:r[k] for k in ("canonical_ablation_run_id","configuration","profile","repetition","repetition_seed","AR","DC","TC","adaptation_latency_ms")} for r in result["run_rows"]]
 figure=[{k:r[k] for k in ("configuration","metric","count","mean","std")} for r in summary]
 configuration={"protocol":"canonical_v15_ablation","experiment_id":result["experiment_id"],**config.to_dict()}
 ablation_manifest={"configurations":manifest(),"without_risk_rule_strategy":"Risk is removed only from Q. Canonical R1-R5 risk predicates remain unchanged as explicitly required.",
  "without_rule_engine_policy":"Use canonical Q and least-used priority-valid scenario; hold difficulty; fixed limited guidance; direct feedback; no repeat.",
  "metrics_invariant":True,"theta_star_access":"simulation outcomes only; no deployable ablation context"}
 report=f"""# Final Canonical V15 Ablation Study\n\nSynthetic matched Monte Carlo evaluation; repetitions are not human participants.\n\nRuns: {len(result['run_rows'])}\nEpisodes: {config.episodes}\nRepetitions: {config.repetitions}\nProfiles: {', '.join(config.profiles)}\nConfigurations: {', '.join(ABLATIONS)}\n\nPaired differences are oriented so positive means Complete Framework is better. No population-level p-values are reported.\n"""
 files={"canonical_ablation_configuration.json":json.dumps(configuration,indent=2).encode(),
  "canonical_ablation_manifest.json":json.dumps(ablation_manifest,indent=2).encode(),
  "canonical_ablation_run_results.csv":_csv(result["run_rows"]),"canonical_ablation_cycle_results.csv":_csv(result["cycle_rows"]),
  "canonical_ablation_summary.csv":_csv(summary),"canonical_ablation_paired_differences.csv":_csv(paired_rows),
  "canonical_ablation_profile_summary.csv":_csv([{**r,"summary_type":"aggregate"} for r in profile_summary]+[{**r,"summary_type":"paired"} for r in profile_pairs]),"canonical_ablation_fixed_posttest_results.csv":_csv(result["posttest_rows"]),
  "canonical_ablation_target_attainment.csv":_csv(target),"canonical_ablation_trace_fidelity.csv":_csv(fidelity),
  "canonical_ablation_figure_data.csv":_csv(figure),"canonical_ablation_report.md":report.encode()}
 for name,value in files.items():(folder/name).write_bytes(value)
 return folder
