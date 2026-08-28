"""Canonical V15 sensitivity summaries, ranks, paired differences, and export."""
from __future__ import annotations
import csv,io,json
from pathlib import Path
from statistics import mean,median,pstdev
import numpy as np
from .canonical_sensitivity import condition_manifest

HIGHER=("CCG_star","canonical_reference_RWCS_star","TAR","AR","DC","TC")
LOWER=("CER","CMR","SOR","episodes_to_target","adaptation_latency_ms")
RANK_METRICS=("CCG_star","canonical_reference_RWCS_star","CER","CMR","TAR","SOR")

def _cell(v):return json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v
def _csv(rows):
 if not rows:return b""
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows({k:_cell(v) for k,v in r.items()} for r in rows);return s.getvalue().encode()
def summarize(rows,groups):
 out=[];bucket={}
 for r in rows:bucket.setdefault(tuple(r[g] for g in groups),[]).append(r)
 for key,vals in sorted(bucket.items()):
  for metric in (*HIGHER,*LOWER,"regime_RWCS_star"):
   nums=[float(r[metric]) for r in vals];out.append({**dict(zip(groups,key)),"metric":metric,"count":len(nums),"mean":round(mean(nums),6),"std":round(pstdev(nums),6)})
 return out
def paired(rows):
 out=[]
 for condition in sorted({r["condition_id"] for r in rows}):
  subset=[r for r in rows if r["condition_id"]==condition];prop={(r["profile"],r["repetition"]):r for r in subset if r["method"]=="proposed"}
  for comparator in sorted({r["method"] for r in subset}-{"proposed"}):
   comp={(r["profile"],r["repetition"]):r for r in subset if r["method"]==comparator};keys=sorted(prop.keys()&comp.keys())
   for metric in (*HIGHER,*LOWER):
    vals=[float(prop[k][metric])-float(comp[k][metric]) if metric in HIGHER else float(comp[k][metric])-float(prop[k][metric]) for k in keys];lo,hi=np.quantile(vals,[.025,.975])
    out.append({"comparison_type":"proposed_vs_method","condition_id":condition,"study_type":subset[0]["study_type"],"parameter_name":subset[0]["parameter_name"],"regime_name":subset[0]["regime_name"],"comparator":comparator,"metric":metric,"orientation":"positive = Proposed is better","mean_paired_difference":round(mean(vals),6),"median_paired_difference":round(median(vals),6),"mc95_lower":round(float(lo),6),"mc95_upper":round(float(hi),6),"win_rate":round(sum(v>0 for v in vals)/len(vals),6),"matched_pairs":len(vals)})
 # Independently quantify each tested Proposed condition relative to the
 # canonical Proposed condition for the same matched profile/repetition.
 by_condition={c:{(r["profile"],r["repetition"]):r for r in rows if r["condition_id"]==c and r["method"]=="proposed"} for c in {r["condition_id"] for r in rows}}
 for condition,current in sorted(by_condition.items()):
  sample=next(r for r in rows if r["condition_id"]==condition);base=canonical_id(sample["parameter_name"]);reference=by_condition.get(base,{})
  keys=sorted(current.keys()&reference.keys())
  if not keys:continue
  for metric in (*HIGHER,*LOWER):
   vals=[float(current[k][metric])-float(reference[k][metric]) if metric in HIGHER else float(reference[k][metric])-float(current[k][metric]) for k in keys];lo,hi=np.quantile(vals,[.025,.975])
   out.append({"comparison_type":"condition_vs_canonical_proposed","condition_id":condition,"study_type":sample["study_type"],"parameter_name":sample["parameter_name"],"regime_name":sample["regime_name"],"comparator":base,"metric":metric,"orientation":"positive = tested condition is better than canonical Proposed","mean_paired_difference":round(mean(vals),6),"median_paired_difference":round(median(vals),6),"mc95_lower":round(float(lo),6),"mc95_upper":round(float(hi),6),"win_rate":round(sum(v>0 for v in vals)/len(vals),6),"matched_pairs":len(vals)})
 return out
def canonical_id(parameter):
 return {"eta":"eta_0p2","rho":"rho_0p18","kappa":"kappa_0p12","observation_weights":"weights_canonical","urgency":"urgency_nominal","latent_dynamics":"latent_canonical","r1_risk":"r1_risk_0p75","r2_risk":"r2_risk_0p5","r3_mastery":"r3_mastery_0p8","repetition_weight":"repetition_weight_0p5","sigma_g":"sigma_g_0p35"}[parameter]
def ranks(rows,paired_rows):
 means={}
 for r in rows:means.setdefault((r["condition_id"],r["method"]),[]).append(r)
 out=[]
 for condition in sorted({r["condition_id"] for r in rows}):
  sample=next(r for r in rows if r["condition_id"]==condition);all_methods=sorted({r["method"] for r in rows if r["condition_id"]==condition});deploy=[m for m in all_methods if m!="oracle"]
  base=canonical_id(sample["parameter_name"])
  scopes=[("deployable",deploy)]
  if "oracle" in all_methods:scopes.append(("all_methods",all_methods))
  for scope,methods in scopes:
   for metric in RANK_METRICS:
    higher=metric not in LOWER;ordered=sorted(methods,key=lambda m:(-mean(float(x[metric]) for x in means[(condition,m)]) if higher else mean(float(x[metric]) for x in means[(condition,m)]),m));rank=ordered.index("proposed")+1
    border=sorted(methods,key=lambda m:(-mean(float(x[metric]) for x in means[(base,m)]) if higher else mean(float(x[metric]) for x in means[(base,m)]),m));base_rank=border.index("proposed")+1
    method_pairs=[pr for pr in paired_rows if pr["comparison_type"]=="proposed_vs_method" and pr["condition_id"]==condition and pr["metric"]==metric and pr["comparator"] in methods]
    directions=[]
    for pr in method_pairs:
     bp=next(x for x in paired_rows if x["comparison_type"]=="proposed_vs_method" and x["condition_id"]==base and x["metric"]==metric and x["comparator"]==pr["comparator"]);directions.append(bool(np.sign(pr["mean_paired_difference"])==np.sign(bp["mean_paired_difference"])))
    out.append({"record_type":"condition","rank_scope":scope,"condition_id":condition,"study_type":sample["study_type"],"parameter_name":sample["parameter_name"],"regime_name":sample["regime_name"],"metric":metric,"proposed_rank":rank,"canonical_rank":base_rank,"rank_unchanged":rank==base_rank,"paired_direction_unchanged_rate":round(mean(directions),6) if directions else 1.0})
 for scope in sorted({r["rank_scope"] for r in out}):
  scoped=[r for r in out if r["rank_scope"]==scope]
  out.append({"record_type":"summary","rank_scope":scope,"condition_id":"ALL","study_type":"rank_stability","parameter_name":"ALL","regime_name":"ALL","metric":"ALL","rank_unchanged":round(mean(bool(r["rank_unchanged"]) for r in scoped),6),"paired_direction_unchanged_rate":round(mean(float(r["paired_direction_unchanged_rate"]) for r in scoped),6)})
 return out

def save_canonical_sensitivity(result,base_config,conditions,definitions,output_root):
 folder=Path(output_root)/result["experiment_id"];folder.mkdir(parents=True,exist_ok=False);rows=result["run_rows"]
 summary=summarize(rows,["condition_id","study_type","parameter_name","parameter_value","regime_name","method"]);profiles=summarize(rows,["condition_id","regime_name","method","profile"]);pairs=paired(rows);rank=ranks(rows,pairs)
 robustness=[r for r in summary if r["study_type"] in ("urgency_robustness","latent_robustness")];robust_pairs=[r for r in pairs if r["comparison_type"]=="proposed_vs_method" and r["study_type"] in ("urgency_robustness","latent_robustness")]
 target=[{k:r[k] for k in ("canonical_sensitivity_run_id","condition_id","method","profile","repetition","repetition_seed","target_reached","episodes_to_target","censored","TAR")} for r in rows]
 config={"protocol":"canonical_v15_sensitivity","experiment_id":result["experiment_id"],"base_config":base_config.to_dict(),"condition_count":len(conditions)};manifest={"conditions":condition_manifest(conditions,base_config,definitions),"ofat":True,"cartesian_product":False,"metrics_invariant":True,"oracle_deployable":False}
 report=f"# Canonical V15 Sensitivity and Robustness\n\nSynthetic matched Monte Carlo study; not parameter optimization.\n\nRuns: {len(rows)}\nConditions: {len(conditions)}\nEpisodes: {base_config.episodes}\nRepetitions: {base_config.repetitions}\n"
 files={"canonical_sensitivity_configuration.json":json.dumps(config,indent=2).encode(),"canonical_sensitivity_manifest.json":json.dumps(manifest,indent=2).encode(),
  "canonical_sensitivity_run_results.csv":_csv(rows),"canonical_sensitivity_summary.csv":_csv(summary),"canonical_sensitivity_profile_summary.csv":_csv(profiles),"canonical_sensitivity_paired_differences.csv":_csv(pairs),"canonical_sensitivity_rank_stability.csv":_csv(rank),"canonical_sensitivity_target_attainment.csv":_csv(target),"canonical_sensitivity_fixed_posttest_results.csv":_csv(result["posttest_rows"]),"canonical_sensitivity_figure_data.csv":_csv(summary),"canonical_robustness_summary.csv":_csv(robustness),"canonical_robustness_paired_differences.csv":_csv(robust_pairs),"canonical_sensitivity_report.md":report.encode()}
 for name,value in files.items():(folder/name).write_bytes(value)
 return folder
