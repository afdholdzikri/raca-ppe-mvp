"""Deterministic scenario selection and difficulty behavior."""

def select_initial_scenario(scenarios) -> str:
    return sorted(scenarios)[0]


def select_next_scenario(current_id, scenarios, priority_ranking, history, repeat_required=False):
    if repeat_required: return current_id
    use_count = {sid: history.count(sid) for sid in scenarios}
    for competence_id, _ in priority_ranking:
        matches = [s.id for s in scenarios.values() if competence_id in s.target_competencies]
        if matches:
            return min(matches, key=lambda sid: (use_count[sid], sid))
    ordered = sorted(scenarios)
    return ordered[(ordered.index(current_id) + 1) % len(ordered)]


def select_priority_alternative(current_id,scenarios,priority_ranking,history):
    """Select the best priority-linked scenario other than the current one."""
    use_count={sid:history.count(sid) for sid in scenarios}
    for competence_id,_ in priority_ranking:
        matches=[s.id for s in scenarios.values()
                 if s.id!=current_id and competence_id in s.target_competencies]
        if matches:
            return min(matches,key=lambda sid:(use_count[sid],sid))
    ordered=sorted(scenarios)
    return ordered[(ordered.index(current_id)+1)%len(ordered)]


def difficulty_behavior(scenario, difficulty, distractor_level, ppe_ids):
    if difficulty not in (1, 2, 3): raise ValueError("difficulty must be between 1 and 3")
    limit_factor = {1: 1.25, 2: 1.0, 3: .8}[difficulty]
    count = {"none": 0, "low": 1, "medium": 2, "high": 3}.get(distractor_level, 1)
    distractors = [x for x in scenario.distractor_pool if x not in scenario.required_ppe][:count]
    # Valid required PPE is never removed; global choices are available at level 3.
    options = list(dict.fromkeys(scenario.required_ppe + distractors))
    if difficulty == 3: options = list(ppe_ids)
    return {"time_limit_seconds": max(10, round(scenario.time_limit_seconds * limit_factor)),
            "ppe_options": options, "emphasized_hazards": scenario.hazards[:1] if difficulty == 1 else scenario.hazards}
