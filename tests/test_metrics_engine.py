from core.metrics_engine import calculate_session_metrics

def test_empty_metrics():
    m=calculate_session_metrics([]); assert m["total_episodes"]==0 and m["mean_competence"]==0

def test_session_metrics():
    base={"scenario_risk":.8,"risk_category":"Critical","hint_used":True,
          "response_time_seconds":10,"adaptation_latency_ms":2,
          "adaptation":"priority_remediation","scenario_id":"S5",
          "competence_after":{"x":.5}}
    traces=[dict(base,correct=False),dict(base,correct=True,hint_used=False)]
    m=calculate_session_metrics(traces,{"x":.6})
    assert m["correct_decision_rate"]==.5; assert m["critical_error_count"]==1
    assert m["hint_usage_rate"]==.5; assert m["mean_adaptation_latency"]==2
