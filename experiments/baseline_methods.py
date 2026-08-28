"""Deterministic comparison methods without Streamlit dependencies."""
from dataclasses import dataclass
from core.scenario_manager import select_next_scenario

@dataclass(frozen=True)
class MethodInput:
    scenario:object; scenarios:dict; competence_scores:dict; repeated_errors:dict
    current_difficulty:int; scenario_history:list; recent_scores:list
    risk_values:dict; config:object; correct:bool; priority_ranking:list

def _next_cyclic(current,scenarios):
    ids=sorted(scenarios); return ids[(ids.index(current)+1)%len(ids)]

class StaticMethod:
    id="static"
    def decide(self,c):
        nxt=_next_cyclic(c.scenario.id,c.scenarios)
        return {"next_scenario":nxt,"next_difficulty":c.scenarios[nxt].base_difficulty,
          "assistance":"limited_visual_guidance","distractor_level":"low","feedback":"direct_explanation",
          "repeat_required":False,"active_rules":["fixed_sequence"],"selected_rule":"fixed_sequence",
          "adaptation":"static_progression","highest_priority_competence":c.priority_ranking[0][0]}

class ScoreAdaptiveMethod:
    id="score_adaptive"
    def decide(self,c):
        score=sum(c.recent_scores[-5:])/len(c.recent_scores[-5:]) if c.recent_scores else 0
        if score>=.8: delta,assist,rule=1,"minimal","high_recent_score"
        elif score<.5: delta,assist,rule=-1,"full_visual_guidance","low_recent_score"
        else: delta,assist,rule=0,"limited_visual_guidance","moderate_recent_score"
        return {"next_scenario":_next_cyclic(c.scenario.id,c.scenarios),
          "next_difficulty":max(c.config.minimum_difficulty,min(c.config.maximum_difficulty,c.current_difficulty+delta)),
          "assistance":assist,"distractor_level":"medium" if delta>=0 else "none",
          "feedback":"summary" if delta>0 else "direct_explanation","repeat_required":False,
          "active_rules":[rule],"selected_rule":rule,"adaptation":"score_adaptive",
          "highest_priority_competence":c.priority_ranking[0][0]}

class CompetenceAdaptiveMethod:
    id="competence_adaptive"
    def decide(self,c):
        gaps={cid:max(0,c.config.target_mastery-value) for cid,value in c.competence_scores.items()}
        target=min(gaps,key=lambda cid:(-gaps[cid],-c.repeated_errors.get(cid,0),cid))
        ranking=[(target,gaps[target])]
        nxt=select_next_scenario(c.scenario.id,c.scenarios,ranking,c.scenario_history,False)
        mastery=c.competence_scores[target]
        if mastery<.5: delta,assist,rule,name=-1,"full_visual_guidance","low_competence","remedial_competence_adaptation"
        elif mastery<.8: delta,assist,rule,name=0,"limited_visual_guidance","developing_competence","progressive_competence_adaptation"
        else: delta,assist,rule,name=1,"minimal","mastered_competence","challenge_competence_adaptation"
        return {"next_scenario":nxt,"next_difficulty":max(c.config.minimum_difficulty,min(c.config.maximum_difficulty,c.current_difficulty+delta)),
          "assistance":assist,"distractor_level":"low" if delta<1 else "high","feedback":"direct_explanation",
          "repeat_required":False,"active_rules":[rule],"selected_rule":rule,"adaptation":name,
          "highest_priority_competence":target}

METHODS={"static":StaticMethod(),"score_adaptive":ScoreAdaptiveMethod(),"competence_adaptive":CompetenceAdaptiveMethod()}
