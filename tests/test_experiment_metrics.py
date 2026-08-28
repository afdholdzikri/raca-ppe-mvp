from core.data_loader import load_all_data
from experiments.experiment_metrics import *

def test_ccg_rwcs_and_zero_rates():
 d=load_all_data(); initial={k:.4 for k in d["competencies"]}; final={k:.6 for k in initial}
 assert critical_competence_gain(initial,final,d["competencies"])==.2
 assert 0<=rwcs(final,competence_risk_weights(d))<=1
 assert safe_rate(1,0)==0
 assert all(value>0 for value in competence_risk_weights(d).values())
def test_trace_completeness_and_consistency():
 assert trace_completeness([{"a":1,"b":2}],{"a","b"})==1
 class M:
  def decide(self,c): return {"x":1}
 assert decision_consistency(M(),None)==1
