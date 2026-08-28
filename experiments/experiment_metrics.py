"""Run metrics for controlled synthetic-participant comparisons."""
from core.risk_engine import calculate_contextual_risk,calculate_scenario_risk

RUN_METRICS=("CCG","RWCS","CER","AR","SE","decision_consistency","trace_completeness","mean_adaptation_latency_ms")

def competence_contextual_risks(data):
    """Return R_hat: maximum mapped contextual risk, without urgency."""
    risks={cid:0.0 for cid in data["competencies"]}
    # Direct hazard mappings provide the primary risk association.
    for hazard in data["hazards"].values():
        risk=calculate_contextual_risk(hazard.probability,hazard.severity,hazard.base_exposure,1.0)
        cid=hazard.associated_competence_id
        risks[cid]=max(risks[cid],risk)
    # Validated scenario target mappings cover cross-cutting competencies such
    # as multi-PPE selection and hazard identification.
    for scenario in data["scenarios"].values():
        risk=calculate_scenario_risk(
            scenario.hazards,data["hazards"],scenario.context_modifier
        )["scenario_risk"]
        for cid in scenario.target_competencies:
            risks[cid]=max(risks[cid],risk)
    return risks

def competence_risk_weights(data):
    """Return RWCS weights W_j=R_hat_j*U_j."""
    risks=competence_contextual_risks(data)
    return {cid:risk*data["competencies"][cid].urgency for cid,risk in risks.items()}

def critical_competence_gain(initial,final,definitions):
    ids=[cid for cid,d in definitions.items() if d.high_risk_related]
    return round(sum(final[c]-initial[c] for c in ids)/len(ids),6) if ids else 0.0

def rwcs(scores,weights):
    denominator=sum(weights.values())
    return round(sum(weights[c]*scores[c] for c in weights)/denominator,6) if denominator else 0.0

def safe_rate(numerator,denominator): return round(numerator/denominator,6) if denominator else 0.0
def trace_completeness(traces,required):
    return round(sum(len(required&set(t))/len(required) for t in traces)/len(traces),6) if traces and required else 0.0
def decision_consistency(method,context):
    return 1.0 if method.decide(context)==method.decide(context) else 0.0

def run_metrics(initial,final,definitions,weights,episodes,target_reached,target_episode,
                max_episodes,traces,required_trace_fields,consistency):
    critical=[e for e in episodes if e["scenario_risk"]>=e["critical_risk_threshold"]]
    return {"CCG":critical_competence_gain(initial,final,definitions),
      "RWCS":rwcs(final,weights),
      "CER":safe_rate(sum(e["critical_error"] for e in critical),len(critical)),
      "AR":safe_rate(sum(e["adaptation_relevant"] for e in episodes),len(episodes)),
      "SE":target_episode if target_reached else max_episodes+1,
      "decision_consistency":consistency,
      "trace_completeness":trace_completeness(traces,required_trace_fields),
      "mean_adaptation_latency_ms":round(sum(e["adaptation_latency_ms"] for e in episodes)/len(episodes),6) if episodes else 0.0,
      "total_critical_decisions":len(critical),"total_critical_errors":sum(e["critical_error"] for e in critical),
      "total_adaptations":len(episodes),"matched_adaptations":sum(e["adaptation_relevant"] for e in episodes)}
