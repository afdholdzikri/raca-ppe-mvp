"""Independent, tolerance-based audit of Version 4 decision traces."""
from __future__ import annotations
from core.learner_model import calculate_observation_score,update_competence
from core.priority_engine import calculate_global_priorities
from core.risk_engine import calculate_scenario_risk
from .domain_adapter import load_domain
from .experiment_metrics import competence_risk_weights
from .validation_export import save_validation_outputs,validation_id

TOLERANCE=1e-4
REQUIRED_FIELDS={"domain","scenario_id","scenario_risk","risk_category","current_difficulty",
 "next_difficulty","response_score","independence_score","competence_before","competence_accuracy",
 "observation_scores","competence_after","repeated_errors","competence_gaps",
 "priority_by_competence","highest_priority_competence","selected_rule","adaptation",
 "repeat_required","next_scenario"}

def _close(left,right,tolerance):
    return abs(float(left)-float(right))<=tolerance

def eligible_rules(risk,mastery,repeated_errors,correct):
    active=[]
    if risk>=.75 and mastery<.60:active.append("critical_risk_low_mastery")
    if risk>=.50 and repeated_errors>=2:active.append("high_risk_repeated_error")
    if mastery>=.80 and risk>=.50 and correct:active.append("high_mastery_high_risk_correct")
    if mastery>=.65 and correct:active.append("stable_mastery_correct")
    active.append("default_reinforcement")
    return active

def audit_trace(trace,tolerance=TOLERANCE,learning_rate=.2,repetition_weight=.5,target_mastery=.8):
    missing=sorted(REQUIRED_FIELDS-set(trace));inconsistent=[];critical=[];recomputed={}
    if missing:return {"completeness_score":round(1-len(missing)/len(REQUIRED_FIELDS),6),
      "consistency_score":0.0,"linkage_score":0.0,"overall_score":0.0,"audit_status":"FAIL",
      "missing_fields":missing,"inconsistent_fields":[],"critical_violations":["missing required fields"],
      "recomputed_values":{},"tolerance":tolerance}
    data=load_domain(trace["domain"]);scenario=data["scenarios"].get(trace["scenario_id"])
    if scenario is None:critical.append("unknown scenario")
    else:
        risk=calculate_scenario_risk(scenario.hazards,data["hazards"],trace.get("context_modifier",scenario.context_modifier))
        recomputed["scenario_risk"]=risk["scenario_risk"];recomputed["risk_category"]=risk["risk_category"]
        if not _close(trace["scenario_risk"],risk["scenario_risk"],tolerance):inconsistent.append("scenario_risk")
        if trace["risk_category"]!=risk["risk_category"]:inconsistent.append("risk_category")
    for cid,accuracy in trace["competence_accuracy"].items():
        observation=calculate_observation_score(bool(accuracy),trace["response_score"],trace["independence_score"])
        after=update_competence(trace["competence_before"][cid],observation,learning_rate)
        recomputed.setdefault("observation_scores",{})[cid]=observation
        recomputed.setdefault("competence_after",{})[cid]=after
        recomputed.setdefault("competence_gaps",{})[cid]=round(max(0,target_mastery-after),6)
        if not _close(trace["observation_scores"][cid],observation,tolerance):inconsistent.append(f"observation_scores.{cid}")
        if not _close(trace["competence_after"][cid],after,tolerance):inconsistent.append(f"competence_after.{cid}")
        if not _close(trace["competence_gaps"][cid],max(0,target_mastery-after),tolerance):inconsistent.append(f"competence_gaps.{cid}")
    weights=competence_risk_weights(data)
    priorities=calculate_global_priorities(weights,trace["competence_after"],trace["repeated_errors"],
      data["competencies"],repetition_weight,target_mastery)
    recomputed["priority_by_competence"]=priorities["priority_by_competence"]
    recomputed["training_priority"]=priorities["priority_by_competence"]
    recomputed["repetition_factors"]={
      cid:round(1+repetition_weight*trace["repeated_errors"].get(cid,0),6)
      for cid in trace["competence_after"]}
    for cid,value in priorities["priority_by_competence"].items():
        if not _close(trace["priority_by_competence"][cid],value,tolerance):inconsistent.append(f"priority_by_competence.{cid}")
    target=priorities["highest_priority_competence"];mastery=trace["competence_after"][target]
    eligible=eligible_rules(trace["scenario_risk"],mastery,trace["repeated_errors"].get(target,0),trace.get("correct",False))
    recomputed["eligible_rules"]=eligible
    linkage=1.0
    if trace["selected_rule"] not in eligible:critical.append("selected rule is ineligible");linkage=0.0
    expected={"critical_risk_low_mastery":"priority_remediation","high_risk_repeated_error":"targeted_remediation",
      "high_mastery_high_risk_correct":"challenge_adaptation","stable_mastery_correct":"progressive_adaptation",
      "default_reinforcement":"reinforcement_adaptation"}
    if expected.get(trace["selected_rule"])!=trace["adaptation"]:critical.append("rule/adaptation contradiction");linkage=0.0
    if not 1<=trace["next_difficulty"]<=3:critical.append("difficulty outside bounds")
    consistency=max(0.0,1-len(set(inconsistent))/max(1,len(REQUIRED_FIELDS)))
    completeness=1.0;overall=round((completeness+consistency+linkage)/3,6)
    return {"completeness_score":completeness,"consistency_score":round(consistency,6),
      "linkage_score":linkage,"overall_score":overall,
      "audit_status":"PASS" if not inconsistent and not critical else "FAIL",
      "missing_fields":[],"inconsistent_fields":sorted(set(inconsistent)),
      "critical_violations":critical,"recomputed_values":recomputed,"tolerance":tolerance}

def run_trace_audit(traces,seed=42,output_dir=None,**_):
    results=[{"trace_index":index,**audit_trace(trace)} for index,trace in enumerate(traces)]
    identifier=validation_id("trace-audit",seed)
    summary={"validation_id":identifier,"trace_count":len(results),
      "passed":sum(row["audit_status"]=="PASS" for row in results),
      "failed":sum(row["audit_status"]!="PASS" for row in results),"tolerance":TOLERANCE}
    files={"trace_audit_results.json":results,"trace_audit_summary.json":summary}
    destination=None;downloads={}
    if output_dir is not None:destination,downloads=save_validation_outputs(files,output_dir,identifier)
    return {"validation_id":identifier,"results":results,"summary":summary,"files":files,
      "downloads":downloads,"output_dir":str(destination) if destination else None}
