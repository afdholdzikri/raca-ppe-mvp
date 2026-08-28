"""Canonical V15 matched Monte Carlo experiment engine."""
from __future__ import annotations
from datetime import datetime,timezone
from statistics import mean
import time
from core.data_loader import load_all_data
from core.priority_engine import calculate_global_priorities
from core.risk_engine import calculate_scenario_risk
from .baseline_methods import MethodInput
from .canonical_config import CanonicalConfig
from .canonical_latent import LatentState,evolve_latent,generate_observations
from .canonical_observable import observation_score,update_engine_estimate
from .canonical_methods import DeployableContext,OracleContext,decide
from .canonical_metrics import latent_outcomes,paired_differences,posttest_metrics,scenario_oscillation_rate
from .experiment_metrics import competence_contextual_risks,competence_risk_weights
from .synthetic_trainee import initial_scores,load_profiles

def _target(theta,definitions,target): return all(theta[c]>=target for c,d in definitions.items() if d.high_risk_related)

def canonical_run_id(method, profile, repetition, config):
    """Return the stable identity of one canonical method/profile repetition."""
    return f"v15-s{config.base_seed}-{profile}-r{repetition}-{method}"


def _fixed_posttest(state,data,config,method,profile,repetition,run_id):
    rows=[]
    repetition_seed=config.repetition_seed(profile,repetition)
    for sid in sorted(data["scenarios"]):
      scenario=data["scenarios"][sid];risk=calculate_scenario_risk(scenario.hazards,data["hazards"],scenario.context_modifier)
      for item in range(config.posttest_repetitions):
        obs=generate_observations(state,scenario,data["ppe"],scenario.base_difficulty,"none",config,
          config.event_seed(profile,repetition,item,f"posttest-{sid}"),scenario.time_limit_seconds)
        selected=set(obs["selected_ppe"]);required=set(scenario.required_ppe)
        critical=risk["scenario_risk"]>=config.critical_risk_threshold
        rows.append({"canonical_run_id":run_id,"method":method,"profile":profile,"repetition":repetition,
          "repetition_seed":repetition_seed,"scenario_id":sid,"item":item,"assistance":"none",
          "scenario_risk":risk["scenario_risk"],"selected_ppe":sorted(selected),"required_ppe":scenario.required_ppe,
          "missing_ppe":sorted(required-selected),"correct":selected==required,
          "critical_error":critical and selected!=required,"critical_miss":critical and bool(required-selected)})
    return rows

def run_single(method,profile_id,repetition,config,experiment_id="canonical"):
    data=load_all_data();profile=load_profiles()[profile_id]; estimate=initial_scores(profile,data["competencies"])
    latent=LatentState(dict(estimate)); initial_theta=latent.snapshot(); errors={c:0 for c in estimate};risk_hat=competence_contextual_risks(data);weights=competence_risk_weights(data)
    sid="S1";difficulty=data["scenarios"][sid].base_difficulty;assistance="limited_visual_guidance";history=[];recent=[];cycles=[]
    rep_seed=config.repetition_seed(profile_id,repetition);run_id=canonical_run_id(method,profile_id,repetition,config);reached_episode=None
    for episode in range(1,config.episodes+1):
      scenario=data["scenarios"][sid];risk=calculate_scenario_risk(scenario.hazards,data["hazards"],scenario.context_modifier)
      obs=generate_observations(latent,scenario,data["ppe"],difficulty,assistance,config,config.event_seed(profile_id,repetition,episode,"response"),scenario.time_limit_seconds)
      before=dict(estimate); z={}
      for cid in scenario.target_competencies:
        z[cid]=observation_score(obs["action_accuracy"][cid],obs["response_quality"],obs["independence"],config)
        estimate[cid]=update_engine_estimate(estimate[cid],z[cid],config.eta)
        errors[cid]=0 if obs["action_accuracy"][cid]>=1 else errors[cid]+1
      priorities=calculate_global_priorities(risk_hat,estimate,errors,data["competencies"],config.repetition_weight,config.target_mastery,3)
      recent.append(mean(z.values()) if z else 0); selected=set(obs["selected_ppe"]);required=set(scenario.required_ppe);correct=selected==required
      mi=MethodInput(scenario,data["scenarios"],dict(estimate),dict(errors),difficulty,history+[sid],recent,risk,config,correct,priorities["priority_ranking"])
      deploy=DeployableContext(mi,weights,data["competencies"],config.event_seed(profile_id,repetition,episode,"method"))
      started=time.perf_counter(); decision=decide(method,OracleContext(deploy,latent.snapshot(),risk_hat) if method=="oracle" else deploy);latency=(time.perf_counter()-started)*1000
      before_theta=latent.snapshot();evolve_latent(latent,set(scenario.target_competencies),difficulty,config)
      reached=_target(latent.theta_star,data["competencies"],config.target_mastery)
      if reached and reached_episode is None:reached_episode=episode
      cycles.append({"experiment_id":experiment_id,"canonical_run_id":run_id,"method":method,"profile":profile_id,"repetition":repetition,"base_seed":config.base_seed,
        "repetition_seed":rep_seed,"episode":episode,"scenario_id":sid,"difficulty":difficulty,"assistance":assistance,
        "scenario_risk":risk["scenario_risk"],"selected_ppe":sorted(selected),"required_ppe":scenario.required_ppe,
        "missing_ppe":sorted(required-selected),"correct":correct,"response_quality":obs["response_quality"],"independence":obs["independence"],
        "engine_estimate_before":before,"observation_scores":z,"engine_estimate_after":dict(estimate),
        "theta_star_before":before_theta,"theta_star_after":latent.snapshot(),"priority_by_competence":priorities["priority_by_competence"],
        "selected_rule":decision["selected_rule"],"adaptation":decision["adaptation"],"next_scenario":decision["next_scenario"],
        "next_difficulty":decision["next_difficulty"],"adaptation_latency_ms":round(latency,6),"target_reached":reached})
      history.append(sid);sid=decision["next_scenario"];difficulty=decision["next_difficulty"];assistance=decision["assistance"]
    post=_fixed_posttest(latent,data,config,method,profile_id,repetition,run_id); outcomes=latent_outcomes(initial_theta,latent.theta_star,data["competencies"],weights,config.target_mastery)
    fidelity={"AR":round(sum(c["next_scenario"] in data["scenarios"] for c in cycles)/len(cycles),6),"DC":1.0,"TC":1.0,"CDRS":1.0}
    run={"experiment_id":experiment_id,"canonical_run_id":run_id,"method":method,"simulation_only":method=="oracle","profile":profile_id,"repetition":repetition,
      "base_seed":config.base_seed,"repetition_seed":rep_seed,"episodes_completed":len(cycles),"target_reached":reached_episode is not None,
      "episodes_to_target":reached_episode or config.episodes,"censored":reached_episode is None,"SOR":scenario_oscillation_rate([c["scenario_id"] for c in cycles]),
      **outcomes,**posttest_metrics(post,config.critical_risk_threshold),**fidelity,"adaptation_latency_ms":round(sum(c["adaptation_latency_ms"] for c in cycles)/len(cycles),6)}
    return cycles,run,post

def run_canonical(config,progress=None):
    eid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-v15";cycles=[];runs=[];post=[];done=0;total=len(config.methods)*len(config.profiles)*config.repetitions
    for profile in config.profiles:
      for repetition in range(config.repetitions):
       for method in config.methods:
        c,r,p=run_single(method,profile,repetition,config,eid);cycles+=c;runs.append(r);post+=p;done+=1
        if progress:progress(done,total)
    return {"experiment_id":eid,"cycle_rows":cycles,"run_rows":runs,"posttest_rows":post,"paired_rows":paired_differences(runs)}
