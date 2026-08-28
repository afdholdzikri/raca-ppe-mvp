"""Research-ready canonical V15 serialization."""
from __future__ import annotations
import csv,io,json,platform,subprocess
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean,pstdev
from .canonical_config import CANONICAL_RULE_DEFINITIONS,METHOD_REGISTRY
from .canonical_latent import ASSISTANCE_ENCODING,DIFFICULTY_ENCODING

def _cell(value): return json.dumps(value,sort_keys=True) if isinstance(value,(dict,list)) else value
def _csv(rows):
    if not rows:return b""
    stream=io.StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows({k:_cell(v) for k,v in row.items()} for row in rows)
    return stream.getvalue().encode("utf-8")
def _summary(rows,groups):
    metrics=("CCG_star","RWCS_star","TAR","CER","CMR","SOR","episodes_to_target","AR","DC","TC","CDRS","adaptation_latency_ms")
    grouped={}
    for row in rows:grouped.setdefault(tuple(row[g] for g in groups),[]).append(row)
    out=[]
    for key,values in sorted(grouped.items()):
      for metric in metrics:
        nums=[r[metric] for r in values];out.append({**dict(zip(groups,key)),"metric":metric,"count":len(nums),"mean":round(mean(nums),6),"std":round(pstdev(nums),6)})
    return out
def _git():
    try:return subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True,timeout=3).stdout.strip()
    except Exception:return None

def save_canonical(result,config,output_dir):
    folder=Path(output_dir)/result["experiment_id"];folder.mkdir(parents=True,exist_ok=False)
    summary=_summary(result["run_rows"],["method"]);profile_summary=_summary(result["run_rows"],["method","profile"])
    target=[{k:r[k] for k in ("method","profile","repetition","repetition_seed","target_reached","episodes_to_target","censored","TAR")} for r in result["run_rows"]]
    definitions={"CCG_star":"mean latent competence gain over critical competencies (higher better)","RWCS_star":"risk-weighted latent competence at run end (higher better)",
      "TAR":"share of latent competencies attaining target mastery (higher better)","CER":"fixed-post-test critical-scenario error rate (lower better)",
      "CMR":"fixed-post-test missing required PPE count / required PPE opportunities (lower better)","SOR":"A-B-A scenario oscillations / eligible transitions (lower better)",
      "episodes_to_target":"first episode attaining latent critical targets; episode limit when censored","AR":"implementation-fidelity adaptation relevance proxy",
      "DC":"decision consistency","TC":"trace completeness","CDRS":"cross-domain rule stability","adaptation_latency_ms":"measured implementation latency, not learning outcome"}
    metadata={"protocol":"canonical_v15","timestamp_utc":datetime.now(timezone.utc).isoformat(),"git_commit":_git(),"python_version":platform.python_version(),
      "base_seed":config.base_seed,"episodes":config.episodes,"repetitions":config.repetitions,"profiles":config.profiles,"methods":config.methods,
      "canonical_parameters":config.to_dict(),"knowledge_base_version":"repository-domain-json","ruleset_version":"R1-R5-deployable-core",
      "metric_definitions":definitions,"oracle_note":"Oracle is privileged simulation-only and excluded from deployable claims."}
    configuration={"protocol":"canonical_v15",**config.to_dict()}
    parameter_manifest={
      "protocol":"canonical_v15",
      "risk_parameters":{"normalization_maximum":187.5,"probability_scale":[1,5],"severity_scale":[1,5],"exposure_scale":[1,5],"context_modifier_positive":True},
      "learner_parameters":{"eta":config.eta,"w_action":config.w_action,"w_response":config.w_response,"w_independence":config.w_independence,"target_mastery":config.target_mastery,
        "response_assistance_coefficient":config.response_assistance_coefficient,"assistance_independence_coefficient":config.assistance_independence_coefficient},
      "latent_parameters":{"rho":config.rho,"kappa":config.kappa,"practice_rate":config.practice_rate,"sigma_g":config.sigma_g,"latent_decay":config.latent_decay},
      "thresholds":{"critical_posttest_risk":config.critical_risk_threshold,"target_mastery":config.target_mastery,"repetition_weight":config.repetition_weight,"risk_categories":{"low_lt":.25,"medium_lt":.50,"high_lt":.75,"critical_gte":.75}},
      "rule_definitions":CANONICAL_RULE_DEFINITIONS,
      "difficulty_encoding":DIFFICULTY_ENCODING,"assistance_encoding":ASSISTANCE_ENCODING,
      "priority":{"competence_gap":"max(0, target_mastery-l)","error_factor":"1 + repetition_weight * min(1, repeated_errors/3)","risk":"R_hat excludes urgency","urgency_application_count":1},
      "rwcs_weight":"W_j = R_hat_j * U_j",
      "episode_limit":config.episodes,"repetitions":config.repetitions,"posttest_repetitions":config.posttest_repetitions,
    }
    files={"canonical_cycle_results.csv":_csv(result["cycle_rows"]),"canonical_run_results.csv":_csv(result["run_rows"]),
      "canonical_summary.csv":_csv(summary),"canonical_profile_summary.csv":_csv(profile_summary),"canonical_paired_differences.csv":_csv(result["paired_rows"]),
      "canonical_fixed_posttest_results.csv":_csv(result["posttest_rows"]),"canonical_target_attainment.csv":_csv(target),
      "canonical_metadata.json":json.dumps(metadata,indent=2).encode(),"canonical_configuration.json":json.dumps(configuration,indent=2).encode(),
      "canonical_method_registry.json":json.dumps(METHOD_REGISTRY,indent=2).encode(),
      "canonical_parameter_manifest.json":json.dumps(parameter_manifest,indent=2,sort_keys=True).encode()}
    report=f"""# Canonical V15 Experiment Report

This is a matched synthetic Monte Carlo evaluation, not a human-subject study.

- Runs: {len(result['run_rows'])}
- Base seed: {config.base_seed}
- Episodes: {config.episodes}
- Repetitions: {config.repetitions}
- Profiles: {', '.join(config.profiles)}
- Methods: {', '.join(config.methods)}

## State separation

The deployable learner estimate `l[j,t]` is updated only from observable score
`z=wA*A+wR*r+wH*h`. Simulation-owned `theta_star[j,t]` generates responses and
evolves using equations (15)-(16): challenge-based practice growth and decay for
unpracticed competencies. Correctness and assistance do not directly increase
latent competence. Only the simulation-only Oracle receives latent state.

## Fixed post-test

Every matched run uses the same scenario/item seed design with no assistance,
adaptation, or state updates. CER is the error share on critical-risk post-test
items. CMR is missing required PPE selections divided by required PPE
opportunities.

## Paired reporting

Differences are oriented so positive means Proposed is better. Oracle rows are
marked as privileged references and are not deployable-comparator claims.
"""
    files["canonical_report.md"]=report.encode()
    for name,value in files.items():(folder/name).write_bytes(value)
    return folder
