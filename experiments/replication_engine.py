"""Cross-domain replication using the unchanged RACA scientific core."""
from __future__ import annotations
import hashlib,time
from pathlib import Path
from core.learner_model import calculate_independence_score,calculate_response_score,competence_correctness,update_multi_competence
from core.priority_engine import calculate_global_priorities
from core.risk_engine import calculate_scenario_risk
from core.scenario_manager import select_initial_scenario
from .domain_adapter import domain_snapshot,initialize_domain_learner,load_domain
from .experiment_config import ExperimentConfig,VALID_PROFILES
from .experiment_metrics import competence_risk_weights,rwcs
from .proposed_method import ProposedMethod
from .baseline_methods import MethodInput
from .simulation_engine import target_reached
from .synthetic_trainee import SyntheticTrainee,episode_seed,load_profiles
from .validation_aggregation import replication_summary,safe_rate
from .validation_export import save_validation_outputs,validation_id

CORE_MODULES=("risk_engine.py","learner_model.py","priority_engine.py","adaptation_engine.py","scenario_manager.py")
CYCLE_REQUIRED={"domain","run_id","profile","repetition","seed","episode","scenario_id","scenario_risk",
 "selected_ppe","required_ppe","correct","competence_before","competence_after","repeated_errors",
 "priority_by_competence","selected_rule","adaptation","next_scenario","next_difficulty",
 "repeat_required","adaptation_latency_ms","cycle_success"}

def core_algorithm_hashes(core_dir=None):
    root=Path(core_dir) if core_dir else Path(__file__).resolve().parent.parent/"core"
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in CORE_MODULES}

def _domain_weights(data):
    return competence_risk_weights(data)

def _run(domain,profile_id,episodes,repetition,seed,learning_rate=.2,repetition_weight=.5,target_mastery=.8,
         critical_risk_threshold=.75,features=None):
    features={"risk_weighting":True,"dynamic_context":True,"error_history":True,
      "adaptive_assistance":True,"decision_trace":True,**(features or {})}
    data=load_domain(domain);profile=load_profiles()[profile_id]
    scores,errors=initialize_domain_learner(data,profile);initial=dict(scores)
    weights=_domain_weights(data)
    if not features["risk_weighting"]:weights={cid:data["competencies"][cid].urgency for cid in data["competencies"]}
    scenario_id=select_initial_scenario(data["scenarios"])
    difficulty=data["scenarios"][scenario_id].base_difficulty;assistance="limited_visual_guidance"
    history=[];recent=[];cycles=[];method=ProposedMethod();reached=False
    run_id=f"{domain}-{profile_id}-{repetition:03d}"
    for episode in range(1,episodes+1):
        scenario=data["scenarios"][scenario_id]
        modifier=scenario.context_modifier if features["dynamic_context"] else 1.0
        risk=calculate_scenario_risk(scenario.hazards,data["hazards"],modifier)
        action=SyntheticTrainee(profile,episode_seed(seed,episode)).act(
          scenario,data["ppe"],scores,difficulty,assistance,risk["scenario_risk"],errors,scenario.time_limit_seconds)
        selected=set(action.selected_ppe);required=set(scenario.required_ppe);correct=selected==required
        response_score=calculate_response_score(action.response_time,scenario.time_limit_seconds)
        independence=calculate_independence_score(action.hint_used);before=dict(scores)
        accuracy=competence_correctness(scenario,selected,data["ppe"])
        update=update_multi_competence(scores,errors,scenario.target_competencies,accuracy,response_score,independence,learning_rate)
        scores,errors=update["competence_scores"],update["repeated_errors"]
        effective_errors=errors if features["error_history"] else {cid:0 for cid in errors}
        priorities=calculate_global_priorities(weights,scores,effective_errors,data["competencies"],repetition_weight,target_mastery)
        recent.append(sum(update["observation_scores"].values())/len(update["observation_scores"]))
        context=MethodInput(scenario,data["scenarios"],dict(scores),dict(errors),difficulty,
          history+[scenario_id],list(recent),risk,ExperimentConfig(methods=["proposed"],
          trainee_profiles=[profile_id],episodes_per_run=episodes,repetitions=1,
          random_seed=seed,learning_rate=learning_rate,repetition_weight=repetition_weight,
          target_mastery=target_mastery),correct,priorities["priority_ranking"])
        if not features["error_history"]:
            context=MethodInput(context.scenario,context.scenarios,context.competence_scores,
              effective_errors,context.current_difficulty,context.scenario_history,
              context.recent_scores,context.risk_values,context.config,context.correct,
              context.priority_ranking)
        started=time.perf_counter();decision=method.decide(context);latency=(time.perf_counter()-started)*1000
        next_valid=decision["next_scenario"] in data["scenarios"];difficulty_valid=1<=decision["next_difficulty"]<=3
        row={"domain":domain,"run_id":run_id,"profile":profile_id,"repetition":repetition,"seed":seed,
          "episode":episode,"scenario_id":scenario_id,"current_difficulty":difficulty,
          "active_hazards":scenario.hazards,
          "hazard_risk_values":risk["hazard_risk_values"],"scenario_risk":risk["scenario_risk"],
          "risk_category":risk["risk_category"],"context_modifier":scenario.context_modifier,
          "selected_ppe":sorted(selected),"required_ppe":sorted(required),
          "missing_ppe":sorted(required-selected),"unnecessary_ppe":sorted(selected-required),"correct":correct,
          "critical_error":bool(not correct and risk["scenario_risk"]>=critical_risk_threshold),
          "response_time":action.response_time,"response_score":response_score,"hint_used":action.hint_used,
          "independence_score":independence,"competence_before":before,
          "competence_accuracy":accuracy,"observation_scores":update["observation_scores"],"competence_after":dict(scores),
          "repeated_errors":dict(errors),"priority_by_competence":priorities["priority_by_competence"],
          "competence_gaps":{cid:round(max(0,target_mastery-value),6) for cid,value in scores.items()},
          "highest_priority_competence":priorities["highest_priority_competence"],
          "selected_rule":decision["selected_rule"],"active_rules":decision["active_rules"],
          "adaptation":decision["adaptation"],"assistance":decision["assistance"],
          "repeat_required":decision["repeat_required"],"next_scenario":decision["next_scenario"],
          "next_difficulty":decision["next_difficulty"],"adaptation_latency_ms":round(latency,6),
          "cycle_success":bool(next_valid and difficulty_valid),"decision_trace_enabled":features["decision_trace"]}
        row["trace_completeness"]=round(len(CYCLE_REQUIRED&set(row))/len(CYCLE_REQUIRED),6) if features["decision_trace"] else 0.0
        cycles.append(row);history.append(scenario_id)
        if not next_valid:break
        scenario_id=decision["next_scenario"];difficulty=decision["next_difficulty"]
        assistance=decision["assistance"] if features["adaptive_assistance"] else "limited_visual_guidance"
        reached=target_reached(scores,data["competencies"],target_mastery)
        if reached:break
    attempted=len(cycles);successful=sum(row["cycle_success"] for row in cycles)
    critical=[row for row in cycles if row["scenario_risk"]>=critical_risk_threshold]
    run={"domain":domain,"run_id":run_id,"profile":profile_id,"repetition":repetition,"seed":seed,
      "episodes_completed":attempted,"attempted_adaptation_cycles":attempted,
      "successful_adaptation_cycles":successful,"CDRS":safe_rate(successful,attempted),
      "scenario_validation_success":float(all(row["scenario_id"] in data["scenarios"] for row in cycles)),
      "rule_execution_success":float(all(bool(row["selected_rule"]) for row in cycles)),
      "trace_completeness":round(sum(row["trace_completeness"] for row in cycles)/attempted,6) if attempted else 0,
      "mean_adaptation_latency_ms":round(sum(row["adaptation_latency_ms"] for row in cycles)/attempted,6) if attempted else 0,
      "target_reached":bool(reached),"initial_RWCS":rwcs(initial,weights),"final_RWCS":rwcs(scores,weights),
      "CER":safe_rate(sum(row["critical_error"] for row in critical),len(critical)),
      "invalid_configuration_count":0}
    return cycles,run,data

def run_cross_domain_replication(domains,profiles,episodes,repetitions,seed,output_dir=None,progress_callback=None):
    if not domains:raise ValueError("at least one domain is required")
    if not profiles or not set(profiles)<=set(VALID_PROFILES):raise ValueError("invalid profiles")
    if episodes<1 or repetitions<1:raise ValueError("episodes and repetitions must be positive")
    identifier=validation_id("replication",seed);cycles=[];runs=[];snapshots={};total=len(domains)*len(profiles)*repetitions;done=0
    for domain in domains:
        data=load_domain(domain);snapshots[domain]=domain_snapshot(data)
        for profile in profiles:
            for repetition in range(repetitions):
                paired_seed=ExperimentConfig(random_seed=seed).paired_seed(profile,repetition)
                cycle_rows,run_row,_=_run(domain,profile,episodes,repetition,paired_seed)
                cycles.extend(cycle_rows);runs.append(run_row);done+=1
                if progress_callback:progress_callback(done,total)
    summary=replication_summary(runs)
    validation=[{"domain":domain,"valid":True,"scenario_count":len(load_domain(domain)["scenarios"]),"invalid_configuration_count":0} for domain in domains]
    hashes=core_algorithm_hashes()
    metadata={"validation_id":identifier,"seed":seed,"domains":list(domains),"profiles":list(profiles),
      "episodes":episodes,"repetitions":repetitions,"synthetic_outcomes":True}
    report=f"# Cross-Domain Replication\n\nSynthetic simulation only.\n\nRuns: {len(runs)}\nCycles: {len(cycles)}\nMean CDRS: {sum(r['CDRS'] for r in runs)/len(runs):.4f}\n"
    files={"replication_cycle_results.csv":cycles,"replication_run_results.csv":runs,
      "replication_summary.csv":summary,"replication_validation_results.csv":validation,
      "domain_knowledge_snapshot.json":snapshots,"core_algorithm_hashes.json":hashes,
      "replication_metadata.json":metadata,"replication_report.md":report}
    destination=None;downloads={}
    if output_dir is not None:destination,downloads=save_validation_outputs(files,output_dir,identifier)
    return {"validation_id":identifier,"cycle_results":cycles,"run_results":runs,"summary":summary,
      "validation_results":validation,"domain_snapshots":snapshots,"core_algorithm_hashes":hashes,
      "metadata":metadata,"files":files,"downloads":downloads,"output_dir":str(destination) if destination else None}
