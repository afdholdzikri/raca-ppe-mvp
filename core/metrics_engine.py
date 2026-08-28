"""Session-level descriptive metrics (not the final experimental RWCS)."""
from collections import Counter

def calculate_session_metrics(traces, competence_scores=None):
    competence_scores = competence_scores or {}
    count = len(traces)
    correct = sum(bool(t["correct"]) for t in traces)
    mean_comp = sum(competence_scores.values()) / len(competence_scores) if competence_scores else 0.0
    weighted, weights = 0.0, 0.0
    for trace in traces:
        risk = trace["scenario_risk"]
        values = trace["competence_after"].values()
        if values:
            weighted += risk * (sum(values) / len(trace["competence_after"]))
            weights += risk
    return {
        "total_episodes": count, "correct_decision_rate": round(correct / count, 4) if count else 0.0,
        "incorrect_decision_rate": round((count-correct) / count, 4) if count else 0.0,
        "mean_competence": round(mean_comp, 4),
        "risk_weighted_competence_indicator": round(weighted / weights, 4) if weights else 0.0,
        "critical_error_count": sum(not t["correct"] and t["risk_category"] == "Critical" for t in traces),
        "hint_usage_rate": round(sum(t["hint_used"] for t in traces) / count, 4) if count else 0.0,
        "mean_response_time": round(sum(t["response_time_seconds"] for t in traces) / count, 4) if count else 0.0,
        "mean_adaptation_latency": round(sum(t["adaptation_latency_ms"] for t in traces) / count, 4) if count else 0.0,
        "adaptation_distribution": dict(Counter(t["adaptation"] for t in traces)),
        "scenario_exposure_count": dict(Counter(t["scenario_id"] for t in traces)),
    }
