"""Matched canonical V15 ablation simulation engine."""
from __future__ import annotations
from datetime import datetime,timezone
from statistics import mean
import time
from core.data_loader import load_all_data
from core.risk_engine import calculate_scenario_risk
from core.scenario_manager import select_next_scenario
from .baseline_methods import MethodInput
from .canonical_ablation import ABLATIONS,ablation_priorities
from .canonical_config import CanonicalConfig
from .canonical_engine import _fixed_posttest,_target
from .canonical_latent import LatentState,evolve_latent,generate_observations,observation_score,update_engine_estimate
from .canonical_metrics import latent_outcomes,posttest_metrics,scenario_oscillation_rate
from .experiment_metrics import competence_contextual_risks,competence_risk_weights
from .proposed_method import ProposedMethod
from .synthetic_trainee import initial_scores,load_profiles

PROTOCOL="canonical_v15_ablation";RULESET_VERSION="canonical-R1-R5-corrected"

def ablation_run_id(configuration,profile,repetition,config):
    return f"v15-ablation-s{config.base_seed}-{configuration}-{profile}-r{repetition}"

def _neutral_decision(mi,ranking):
    nxt=select_next_scenario(mi.scenario.id,mi.scenarios,ranking,mi.scenario_history,False)
    return {"next_scenario":nxt,"next_difficulty":mi.current_difficulty,
      "assistance":"limited_visual_guidance","feedback":"direct_explanation",
      "repeat_required":False,"selected_rule":"rule_engine_disabled",
      "adaptation":"neutral_configuration","highest_priority_competence":ranking[0][0]}

def run_ablation_single(configuration,profile_id,repetition,config,experiment_id="canonical-ablation"):
    spec=ABLATIONS[configuration];data=load_all_data();profile=load_profiles()[profile_id]
    estimate=initial_scores(profile,data["competencies"]);latent=LatentState(dict(estimate));initial_theta=latent.snapshot()
    errors={c:0 for c in estimate};risk_hat=competence_contextual_risks(data);weights=competence_risk_weights(data)
    sid="S1";difficulty=data["scenarios"][sid].base_difficulty
    assistance="limited_visual_guidance" if spec.adaptive_assistance else "none"
    history=[];recent=[];cycles=[];reached_episode=None;run_id=ablation_run_id(configuration,profile_id,repetition,config)
    rep_seed=config.repetition_seed(profile_id,repetition)
    for episode in range(1,config.episodes+1):
      scenario=data["scenarios"][sid];risk=calculate_scenario_risk(scenario.hazards,data["hazards"],scenario.context_modifier)
      obs=generate_observations(latent,scenario,data["ppe"],difficulty,assistance,config,config.event_seed(profile_id,repetition,episode,"response"),scenario.time_limit_seconds)
      before=dict(estimate);z={}
      for cid in scenario.target_competencies:
        z[cid]=observation_score(obs["action_accuracy"][cid],obs["response_quality"],obs["independence"],config)
        estimate[cid]=update_engine_estimate(estimate[cid],z[cid],config.eta)
        errors[cid]=0 if obs["action_accuracy"][cid]>=1 else errors[cid]+1
      q,ranking=ablation_priorities(spec,risk_hat,estimate,errors,data["competencies"],config.target_mastery,config.repetition_weight)
      recent.append(mean(z.values()) if z else 0);selected=set(obs["selected_ppe"]);required=set(scenario.required_ppe);correct=selected==required
      mi=MethodInput(scenario,data["scenarios"],dict(estimate),dict(errors),difficulty,history+[sid],recent,risk,config,correct,ranking)
      started=time.perf_counter();decision=ProposedMethod().decide(mi) if spec.rule_engine else _neutral_decision(mi,ranking)
      if not spec.adaptive_assistance:decision={**decision,"assistance":"none"}
      latency=(time.perf_counter()-started)*1000;before_theta=latent.snapshot();evolve_latent(latent,set(scenario.target_competencies),difficulty,config)
      reached=_target(latent.theta_star,data["competencies"],config.target_mastery)
      if reached and reached_episode is None:reached_episode=episode
      cycles.append({"experiment_id":experiment_id,"canonical_ablation_run_id":run_id,"configuration":configuration,
        "profile":profile_id,"repetition":repetition,"repetition_seed":rep_seed,"base_seed":config.base_seed,"episodes":config.episodes,
        "protocol":PROTOCOL,"ruleset_version":RULESET_VERSION,"episode":episode,"scenario_id":sid,"difficulty":difficulty,
        "assistance":assistance,"scenario_risk":risk["scenario_risk"],"selected_ppe":sorted(selected),"required_ppe":scenario.required_ppe,
        "missing_ppe":sorted(required-selected),"correct":correct,"response_quality":obs["response_quality"],"independence":obs["independence"],
        "engine_estimate_before":before,"observation_scores":z,"engine_estimate_after":dict(estimate),
        "theta_star_before":before_theta,"theta_star_after":latent.snapshot(),"priority_by_competence":q,
        "selected_rule":decision["selected_rule"],"adaptation":decision["adaptation"],"next_scenario":decision["next_scenario"],
        "next_difficulty":decision["next_difficulty"],"adaptation_latency_ms":round(latency,6),"target_reached":reached})
      history.append(sid);sid=decision["next_scenario"];difficulty=decision["next_difficulty"];assistance=decision["assistance"]
    post=_fixed_posttest(latent,data,config,configuration,profile_id,repetition,run_id)
    for row in post:
      row["canonical_ablation_run_id"]=row.pop("canonical_run_id");row["configuration"]=row.pop("method")
      row.update({"base_seed":config.base_seed,"episodes":config.episodes,"protocol":PROTOCOL,"ruleset_version":RULESET_VERSION})
    outcomes=latent_outcomes(initial_theta,latent.theta_star,data["competencies"],weights,config.target_mastery)
    fidelity={"AR":round(sum(c["next_scenario"] in data["scenarios"] for c in cycles)/len(cycles),6),"DC":1.0,
      "TC":1.0 if spec.decision_trace else 0.0,"adaptation_latency_ms":round(mean(c["adaptation_latency_ms"] for c in cycles),6)}
    run={"experiment_id":experiment_id,"canonical_ablation_run_id":run_id,"configuration":configuration,"profile":profile_id,
      "repetition":repetition,"repetition_seed":rep_seed,"base_seed":config.base_seed,"episodes":config.episodes,"protocol":PROTOCOL,
      "ruleset_version":RULESET_VERSION,"target_reached":reached_episode is not None,"episodes_to_target":reached_episode or config.episodes,
      "censored":reached_episode is None,"SOR":scenario_oscillation_rate([c["scenario_id"] for c in cycles]),**outcomes,
      **posttest_metrics(post,config.critical_risk_threshold),**fidelity}
    return cycles,run,post

def run_canonical_ablation(config,progress=None):
    eid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-v15-ablation";cycles=[];runs=[];post=[];done=0
    total=len(ABLATIONS)*len(config.profiles)*config.repetitions
    for profile in config.profiles:
      for repetition in range(config.repetitions):
       for configuration in ABLATIONS:
        c,r,p=run_ablation_single(configuration,profile,repetition,config,eid);cycles+=c;runs.append(r);post+=p;done+=1
        if progress:progress(done,total)
    return {"experiment_id":eid,"cycle_rows":cycles,"run_rows":runs,"posttest_rows":post}
