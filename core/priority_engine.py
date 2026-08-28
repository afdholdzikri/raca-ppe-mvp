"""Risk-weighted training priority by competence."""


def calculate_priorities(scenario_risk, target_competencies, scores, errors, definitions,
                         repetition_weight=.5, target_mastery=None,
                         error_saturation=None) -> dict:
    if not 0 <= scenario_risk <= 1: raise ValueError("scenario_risk must be between 0 and 1")
    if repetition_weight < 0: raise ValueError("repetition_weight must be non-negative")
    values = {}
    components = {}
    for cid in target_competencies:
        if cid not in definitions or cid not in scores: raise ValueError(f"unknown competence: {cid}")
        error_count = errors.get(cid, 0)
        if (
            isinstance(error_count, bool)
            or not isinstance(error_count, int)
            or error_count < 0
        ):
            raise ValueError(f"repeated errors for {cid} must be a non-negative integer")
        definition = definitions[cid]
        target = definition.target_mastery if target_mastery is None else target_mastery
        gap = max(0, target - scores[cid])
        if error_saturation is None:
            repetition_factor=1+repetition_weight*error_count
        else:
            if error_saturation<=0: raise ValueError("error_saturation must be positive")
            repetition_factor=1+repetition_weight*min(1,error_count/error_saturation)
        priority = round(scenario_risk * gap * repetition_factor * definition.urgency, 4)
        values[cid] = priority
        components[cid] = {
            "risk_hat": scenario_risk,
            "competence_gap": gap,
            "repetition_factor": repetition_factor,
            "urgency": definition.urgency,
            "priority": priority,
        }
    ranking = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    return {"priority_by_competence": values,
            "highest_priority_competence": ranking[0][0] if ranking else None,
            "highest_priority_value": ranking[0][1] if ranking else 0.0,
            "priority_ranking": ranking,
            "priority_components": components}


def calculate_global_priorities(risk_by_competence, scores, errors, definitions,
                                repetition_weight=.5, target_mastery=None,
                                error_saturation=None):
    """Rank all competencies using their mapped risk and the canonical formula."""
    values={}
    components={}
    for competence_id in definitions:
        result=calculate_priorities(
            risk_by_competence.get(competence_id,0.0),
            [competence_id],scores,errors,definitions,
            repetition_weight,target_mastery,error_saturation,
        )
        values[competence_id]=result["highest_priority_value"]
        components[competence_id]=result["priority_components"][competence_id]
    ranking=sorted(values.items(),key=lambda item:(-item[1],item[0]))
    return {"priority_by_competence":values,
      "highest_priority_competence":ranking[0][0] if ranking else None,
      "highest_priority_value":ranking[0][1] if ranking else 0.0,
      "priority_ranking":ranking,"priority_components":components}
