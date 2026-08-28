"""Adapter exposing the Version 2 proposed framework to experiments."""
from core.adaptation_engine import choose_adaptation_v2
from core.scenario_manager import select_next_scenario,select_priority_alternative

class ProposedMethod:
    id="proposed"
    def decide(self,c):
        target=c.priority_ranking[0][0]; mastery=c.competence_scores[target]
        decision=choose_adaptation_v2(c.risk_values["scenario_risk"],mastery,
            c.repeated_errors.get(target,0),0,False,c.current_difficulty,c.correct,
            (sum(c.recent_scores[-3:])/len(c.recent_scores[-3:])-.5) if c.recent_scores else 0)
        nxt=select_next_scenario(c.scenario.id,c.scenarios,c.priority_ranking,
            c.scenario_history,decision["repeat_required"])
        requested_action={
            "next_scenario":nxt,"next_difficulty":decision["next_difficulty"],
            "assistance":decision["assistance"],"feedback":decision["feedback"],
            "repeat_required":decision["repeat_required"],
        }
        bounded_rotation_triggered=False
        consecutive=0
        for scenario_id in reversed(c.scenario_history):
            if scenario_id!=c.scenario.id: break
            consecutive+=1
        if nxt==c.scenario.id and consecutive>=2:
            nxt=select_priority_alternative(
                c.scenario.id,c.scenarios,c.priority_ranking,c.scenario_history
            )
            decision={**decision,"repeat_required":False,
                "active_rules":decision["active_rules"]+["bounded_remediation_rotation"]}
            bounded_rotation_triggered=True
        applied_action={
            "next_scenario":nxt,"next_difficulty":decision["next_difficulty"],
            "assistance":decision["assistance"],"feedback":decision["feedback"],
            "repeat_required":decision["repeat_required"],
        }
        return {**decision,"next_scenario":nxt,"highest_priority_competence":target,
            "requested_action":requested_action,"applied_action":applied_action,
            "bounded_rotation_triggered":bounded_rotation_triggered}
