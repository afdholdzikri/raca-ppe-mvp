"""UI-independent deterministic batch simulation."""
from datetime import datetime,timezone
import time,uuid
from core.data_loader import load_all_data
from core.learner_model import (calculate_independence_score,calculate_response_score,
    competence_correctness,update_multi_competence)
from core.priority_engine import calculate_global_priorities
from core.risk_engine import calculate_scenario_risk
from .baseline_methods import METHODS,MethodInput
from .proposed_method import ProposedMethod
from .synthetic_trainee import SyntheticTrainee,episode_seed,initial_scores,load_profiles
from .experiment_metrics import competence_risk_weights,decision_consistency,run_metrics,rwcs
from .aggregation import aggregate_all,aggregate_results,figure5_data,figure6_data,overall_performance_table

EXPERIMENT_TRACE_FIELDS={"experiment_id","run_id","repetition","seed","method","trainee_profile",
"episode","scenario_id","difficulty","assistance","distractor_level","active_hazards",
"scenario_risk","risk_category","selected_ppe","required_ppe","missing_ppe","unnecessary_ppe",
"correct","critical_error","response_time","response_score","hint_used","independence_score",
"competence_before","observation_scores","competence_after","repeated_errors","competence_gaps",
"priority_by_competence","highest_priority_competence","adaptation","selected_rule",
"next_scenario","next_difficulty","adaptation_relevant","adaptation_latency_ms","target_reached"}
RUN_REQUIRED_FIELDS={"experiment_id","run_id","method","trainee_profile","repetition","seed",
"episodes_completed","target_reached","episode_target_reached","initial_competence",
"final_competence","initial_RWCS","final_RWCS","CCG","RWCS","CER","AR","SE",
"decision_consistency","trace_completeness","mean_adaptation_latency_ms",
"total_critical_decisions","total_critical_errors","total_adaptations","matched_adaptations"}

def target_reached(scores,definitions,target):
    high=[cid for cid,d in definitions.items() if d.high_risk_related]
    return all(scores[c]>=target for c in high) and sum(scores.values())/len(scores)>=target-.05

def run_single_experiment(method_id,trainee_profile_id,config,seed,repetition=0,experiment_id="experiment"):
    data=load_all_data(); profiles=load_profiles()
    if method_id not in (*METHODS,"proposed"): raise ValueError(f"unknown method {method_id}")
    if trainee_profile_id not in profiles: raise ValueError(f"unknown profile {trainee_profile_id}")
    method=ProposedMethod() if method_id=="proposed" else METHODS[method_id]
    profile=profiles[trainee_profile_id]; scores=initial_scores(profile,data["competencies"])
    initial=dict(scores); errors={cid:0 for cid in scores}
    weights=competence_risk_weights(data); initial_rwcs=rwcs(scores,weights)
    scenario_id="S1"; difficulty=data["scenarios"][scenario_id].base_difficulty
    assistance="limited_visual_guidance"; distractor="low"; history=[]; recent=[]; episodes=[]; traces=[]
    reached=False; reached_episode=config.episodes_per_run+1
    run_id=f"{method_id}-{trainee_profile_id}-{repetition:03d}"
    for episode in range(1,config.episodes_per_run+1):
        scenario=data["scenarios"][scenario_id]
        risk=calculate_scenario_risk(scenario.hazards,data["hazards"],scenario.context_modifier)
        # Every method/profile/repetition receives the same episode child seed.
        # Scenario divergence can change within-episode consumption, but cannot
        # shift the random stream used by later episodes.
        trainee=SyntheticTrainee(profile,episode_seed(seed,episode))
        action=trainee.act(scenario,data["ppe"],scores,difficulty,assistance,risk["scenario_risk"],errors,scenario.time_limit_seconds)
        selected=set(action.selected_ppe); required=set(scenario.required_ppe); correct=selected==required
        response_score=calculate_response_score(action.response_time,scenario.time_limit_seconds)
        independence=calculate_independence_score(action.hint_used)
        before=dict(scores)
        accuracy=competence_correctness(scenario,selected,data["ppe"])
        updated=update_multi_competence(scores,errors,scenario.target_competencies,accuracy,
            response_score,independence,config.learning_rate)
        scores,errors=updated["competence_scores"],updated["repeated_errors"]
        priorities=calculate_global_priorities(weights,scores,errors,
            data["competencies"],config.repetition_weight,config.target_mastery)
        recent.append(sum(updated["observation_scores"].values())/len(updated["observation_scores"]))
        context=MethodInput(scenario,data["scenarios"],dict(scores),dict(errors),difficulty,
            history+[scenario_id],list(recent),risk,config,correct,priorities["priority_ranking"])
        started=time.perf_counter(); decision=method.decide(context)
        latency=(time.perf_counter()-started)*1000
        consistency=decision_consistency(method,context)
        external_target=priorities["highest_priority_competence"]
        next_targets=data["scenarios"][decision["next_scenario"]].target_competencies
        relevant=external_target in next_targets or (decision["repeat_required"] and not correct and risk["scenario_risk"]>=config.critical_risk_threshold)
        reached=target_reached(scores,data["competencies"],config.target_mastery)
        if reached and reached_episode==config.episodes_per_run+1: reached_episode=episode
        row={"experiment_id":experiment_id,"run_id":run_id,"repetition":repetition,"seed":seed,
          "method":method_id,"trainee_profile":trainee_profile_id,"episode":episode,
          "scenario_id":scenario_id,"difficulty":difficulty,"assistance":assistance,
          "distractor_level":distractor,"active_hazards":scenario.hazards,
          "hazard_risk_values":risk["hazard_risk_values"],
          "scenario_risk":risk["scenario_risk"],"mean_risk":risk["mean_risk"],
          "risk_category":risk["risk_category"],"context_modifier":scenario.context_modifier,
          "selected_ppe":sorted(selected),"required_ppe":scenario.required_ppe,
          "missing_ppe":sorted(required-selected),"unnecessary_ppe":sorted(selected-required),
          "correct":correct,"critical_error":bool(not correct and risk["scenario_risk"]>=config.critical_risk_threshold),
          "critical_risk_threshold":config.critical_risk_threshold,
          "response_time":action.response_time,"response_score":response_score,
          "hint_used":action.hint_used,"independence_score":independence,
          "competence_before":before,"observation_scores":updated["observation_scores"],
          "competence_after":dict(scores),"repeated_errors":dict(errors),
          "competence_gaps":{c:round(max(0,config.target_mastery-scores[c]),6) for c in scores},
          "priority_by_competence":priorities["priority_by_competence"],
          "highest_priority_competence":external_target,"adaptation":decision["adaptation"],
          "active_rules":decision["active_rules"],"selected_rule":decision["selected_rule"],
          "repeat_required":decision["repeat_required"],"next_assistance":decision["assistance"],
          "feedback":decision["feedback"],"next_scenario":decision["next_scenario"],
          "next_difficulty":decision["next_difficulty"],"adaptation_relevant":bool(relevant),
          "adaptation_latency_ms":round(latency,6),"target_reached":reached,
          "current_RWCS":rwcs(scores,weights),"decision_consistency":consistency}
        episodes.append(row)
        if config.save_decision_traces: traces.append(dict(row))
        history.append(scenario_id); scenario_id=decision["next_scenario"]
        difficulty=decision["next_difficulty"]; assistance=decision["assistance"]; distractor=decision["distractor_level"]
        if reached: break
    metrics=run_metrics(initial,scores,data["competencies"],weights,episodes,reached,reached_episode,
        config.episodes_per_run,traces,EXPERIMENT_TRACE_FIELDS,
        sum(e["decision_consistency"] for e in episodes)/len(episodes))
    run={"experiment_id":experiment_id,"run_id":run_id,"method":method_id,
      "trainee_profile":trainee_profile_id,"repetition":repetition,"seed":seed,
      "episodes_completed":len(episodes),"target_reached":reached,
      "episode_target_reached":reached_episode,"initial_competence":initial,
      "final_competence":scores,"initial_RWCS":initial_rwcs,"final_RWCS":rwcs(scores,weights),**metrics}
    return {"episode_rows":episodes if config.save_episode_logs else [],
      "run_row":run,"decision_traces":traces}

def run_batch_experiments(config,progress_callback=None):
    experiment_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-"+config.config_hash()
    episodes=[]; runs=[]; traces=[]; total=len(config.methods)*len(config.trainee_profiles)*config.repetitions; done=0
    started=time.perf_counter()
    for method in config.methods:
        for profile in config.trainee_profiles:
            for repetition in range(config.repetitions):
                seed=config.paired_seed(profile,repetition)
                result=run_single_experiment(method,profile,config,seed,repetition,experiment_id)
                episodes.extend(result["episode_rows"]); runs.append(result["run_row"]); traces.extend(result["decision_traces"])
                done+=1
                if progress_callback: progress_callback(done,total)
    return {"experiment_id":experiment_id,"config":config.to_dict(),"episode_rows":episodes,
      "run_rows":runs,"decision_traces":traces,"aggregated":aggregate_results(runs).to_dict("records"),
      "aggregated_all":aggregate_all(runs).to_dict("records"),
      "overall_table":overall_performance_table(runs).to_dict("records"),
      "figure5_data":figure5_data(runs).to_dict("records"),
      "figure6_data":figure6_data(episodes,config.episodes_per_run).to_dict("records"),
      "elapsed_seconds":round(time.perf_counter()-started,4)}
