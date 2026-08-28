"""Canonical V15 OFAT sensitivity and latent-robustness simulation."""
from __future__ import annotations
from datetime import datetime,timezone
from statistics import mean
import time
from core.data_loader import load_all_data
from core.risk_engine import calculate_scenario_risk
from core.scenario_manager import select_next_scenario,select_priority_alternative
from .baseline_methods import MethodInput
from .canonical_config import CanonicalConfig
from .canonical_engine import _fixed_posttest,_target
from .canonical_latent import LatentState,evolve_latent,generate_observations,observation_score,update_engine_estimate
from .canonical_methods import DeployableContext,OracleContext,decide
from .canonical_metrics import latent_outcomes,posttest_metrics,scenario_oscillation_rate
from .canonical_sensitivity import effective_urgencies
from .experiment_metrics import competence_contextual_risks,competence_risk_weights
from .synthetic_trainee import initial_scores,load_profiles

PROTOCOL="canonical_v15_sensitivity";RULESET="canonical-R1-R5-corrected"

def sensitivity_run_id(condition,method,profile,repetition,base_seed):return f"v15-sensitivity-s{base_seed}-{condition.id}-{method}-{profile}-r{repetition}"

def sensitivity_priorities(risk_hat,scores,errors,definitions,urgencies,target,repetition_weight):
    values={cid:round(risk_hat[cid]*max(0,target-scores[cid])*(1+repetition_weight*min(1,errors.get(cid,0)/3))*urgencies[cid],4) for cid in definitions}
    return values,sorted(values.items(),key=lambda x:(-x[1],x[0]))

def _proposed_decision(condition,mi,ranking):
    target=ranking[0][0];mastery=mi.competence_scores[target];active=[]
    if mi.risk_values["scenario_risk"]>=condition.r1_risk and mastery<.60:active.append("critical_risk_low_mastery")
    if mi.risk_values["scenario_risk"]>=condition.r2_risk and mi.repeated_errors.get(target,0)>=2:active.append("high_risk_repeated_error")
    if mastery>=condition.r3_mastery and mi.risk_values["scenario_risk"]>=.50 and mi.correct:active.append("high_mastery_high_risk_correct")
    if mastery>=.65 and mi.correct:active.append("stable_mastery_correct")
    active.append("default_reinforcement");selected=active[0]
    rules={"critical_risk_low_mastery":("priority_remediation",-1,"full_visual_guidance","immediate_corrective",True),
      "high_risk_repeated_error":("targeted_remediation",-1,"limited_visual_guidance","immediate_explanation",True),
      "high_mastery_high_risk_correct":("challenge_adaptation",1,"none","delayed_reflective",False),
      "stable_mastery_correct":("progressive_adaptation",1,"minimal","summary",False),
      "default_reinforcement":("reinforcement_adaptation",0,"limited_visual_guidance","direct_explanation",False)}
    adaptation,delta,assistance,feedback,repeat=rules[selected]
    nxt=select_next_scenario(mi.scenario.id,mi.scenarios,ranking,mi.scenario_history,repeat)
    consecutive=0
    for sid in reversed(mi.scenario_history):
      if sid!=mi.scenario.id:break
      consecutive+=1
    if nxt==mi.scenario.id and consecutive>=2:
      nxt=select_priority_alternative(mi.scenario.id,mi.scenarios,ranking,mi.scenario_history);repeat=False;active.append("bounded_remediation_rotation")
    return {"next_scenario":nxt,"next_difficulty":max(1,min(3,mi.current_difficulty+delta)),"assistance":assistance,
      "feedback":feedback,"repeat_required":repeat,"selected_rule":selected,"adaptation":adaptation,"active_rules":active,"highest_priority_competence":target}

def run_sensitivity_single(condition,method,profile_id,repetition,base_config,experiment_id="sensitivity"):
    config=condition.config(base_config);data=load_all_data();profile=load_profiles()[profile_id]
    estimate=initial_scores(profile,data["competencies"]);latent=LatentState(dict(estimate));initial_theta=latent.snapshot();errors={c:0 for c in estimate}
    risk_hat=competence_contextual_risks(data);canonical_weights=competence_risk_weights(data);urgencies,deltas=effective_urgencies(data["competencies"],condition.urgency_regime,base_config.base_seed)
    regime_weights={cid:risk_hat[cid]*urgencies[cid] for cid in risk_hat};sid="S1";difficulty=data["scenarios"][sid].base_difficulty
    assistance="limited_visual_guidance";history=[];recent=[];sequence=[];reached_episode=None;latencies=[]
    run_id=sensitivity_run_id(condition,method,profile_id,repetition,base_config.base_seed);rep_seed=base_config.repetition_seed(profile_id,repetition)
    for episode in range(1,config.episodes+1):
      scenario=data["scenarios"][sid];risk=calculate_scenario_risk(scenario.hazards,data["hazards"],scenario.context_modifier)
      obs=generate_observations(latent,scenario,data["ppe"],difficulty,assistance,config,config.event_seed(profile_id,repetition,episode,"response"),scenario.time_limit_seconds)
      z={}
      for cid in scenario.target_competencies:
       z[cid]=observation_score(obs["action_accuracy"][cid],obs["response_quality"],obs["independence"],config);estimate[cid]=update_engine_estimate(estimate[cid],z[cid],config.eta);errors[cid]=0 if obs["action_accuracy"][cid]>=1 else errors[cid]+1
      q,ranking=sensitivity_priorities(risk_hat,estimate,errors,data["competencies"],urgencies,config.target_mastery,config.repetition_weight)
      recent.append(mean(z.values()) if z else 0);selected=set(obs["selected_ppe"]);required=set(scenario.required_ppe);correct=selected==required
      mi=MethodInput(scenario,data["scenarios"],dict(estimate),dict(errors),difficulty,history+[sid],recent,risk,config,correct,ranking)
      context=DeployableContext(mi,canonical_weights,data["competencies"],config.event_seed(profile_id,repetition,episode,"method"));start=time.perf_counter()
      if method=="proposed":decision=_proposed_decision(condition,mi,ranking)
      elif method=="oracle":decision=decide(method,OracleContext(context,latent.snapshot(),risk_hat))
      else:decision=decide(method,context)
      latencies.append((time.perf_counter()-start)*1000);evolve_latent(latent,set(scenario.target_competencies),difficulty,config)
      if _target(latent.theta_star,data["competencies"],config.target_mastery) and reached_episode is None:reached_episode=episode
      sequence.append(sid);history.append(sid);sid=decision["next_scenario"];difficulty=decision["next_difficulty"];assistance=decision["assistance"]
    post=_fixed_posttest(latent,data,config,f"{condition.id}:{method}",profile_id,repetition,run_id)
    for row in post:
      row["canonical_sensitivity_run_id"]=row.pop("canonical_run_id");row.pop("method");row.update({"study_type":condition.study_type,"parameter_name":condition.parameter_name,"parameter_value":condition.parameter_value,"regime_name":condition.regime_name,"method":method,"base_seed":base_config.base_seed,"episodes":config.episodes,"protocol":PROTOCOL,"ruleset_version":RULESET})
    canonical=latent_outcomes(initial_theta,latent.theta_star,data["competencies"],canonical_weights,config.target_mastery);regime=latent_outcomes(initial_theta,latent.theta_star,data["competencies"],regime_weights,config.target_mastery)
    row={"experiment_id":experiment_id,"canonical_sensitivity_run_id":run_id,"study_type":condition.study_type,"parameter_name":condition.parameter_name,"parameter_value":condition.parameter_value,"regime_name":condition.regime_name,"condition_id":condition.id,"method":method,"profile":profile_id,"repetition":repetition,"repetition_seed":rep_seed,"base_seed":base_config.base_seed,"episodes":config.episodes,"protocol":PROTOCOL,"ruleset_version":RULESET,
      "w_A":config.w_action,"w_R":config.w_response,"w_H":config.w_independence,"kappa":config.kappa,"response_assistance_coefficient":config.response_assistance_coefficient,"resolved_lambda_a":config.assistance_independence_coefficient,
      "nominal_urgency":{cid:d.urgency for cid,d in data["competencies"].items()},"effective_urgency":urgencies,"practice_rate":config.practice_rate,"sigma_g":config.sigma_g,"latent_decay":config.latent_decay,
      "target_reached":reached_episode is not None,"episodes_to_target":reached_episode or config.episodes,"censored":reached_episode is None,"SOR":scenario_oscillation_rate(sequence),"CCG_star":canonical["CCG_star"],"RWCS_star":canonical["RWCS_star"],"canonical_reference_RWCS_star":canonical["RWCS_star"],"regime_RWCS_star":regime["RWCS_star"],"TAR":canonical["TAR"],**posttest_metrics(post,config.critical_risk_threshold),"AR":1.0,"DC":1.0,"TC":1.0,"adaptation_latency_ms":round(mean(latencies),6)}
    return row,post

def run_canonical_sensitivity(base_config,conditions,progress=None):
    eid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-v15-sensitivity";runs=[];post=[];total=sum(len(c.methods) for c in conditions)*len(base_config.profiles)*base_config.repetitions;done=0
    for condition in conditions:
      for profile in base_config.profiles:
       for repetition in range(base_config.repetitions):
        for method in condition.methods:
         row,p=run_sensitivity_single(condition,method,profile,repetition,base_config,eid);runs.append(row);post+=p;done+=1
         if progress:progress(done,total)
    return {"experiment_id":eid,"run_rows":runs,"posttest_rows":post}
