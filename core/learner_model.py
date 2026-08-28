"""Transparent learner-observation and competence updates."""


def _validate_unit(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")


def calculate_observation_score(
    correct: bool,
    response_score: float = 1.0,
    independence_score: float = 1.0,
) -> float:
    """Combine action accuracy, response quality, and independence."""
    if not isinstance(correct, bool):
        raise ValueError("correct must be a boolean")
    _validate_unit("response_score", response_score)
    _validate_unit("independence_score", independence_score)
    action_accuracy = 1.0 if correct else 0.0
    score = 0.60 * action_accuracy + 0.20 * response_score + 0.20 * independence_score
    return round(score, 4)


def update_competence(
    current_competence: float,
    observation_score: float,
    learning_rate: float = 0.20,
) -> float:
    """Update competence using an exponential moving average."""
    _validate_unit("current_competence", current_competence)
    _validate_unit("observation_score", observation_score)
    if (
        isinstance(learning_rate, bool)
        or not isinstance(learning_rate, (int, float))
        or not 0 < learning_rate <= 1
    ):
        raise ValueError("learning_rate must be greater than 0 and at most 1")
    updated = (1 - learning_rate) * current_competence + learning_rate * observation_score
    return round(max(0.0, min(1.0, updated)), 4)


def initialize_learner(competencies) -> tuple[dict[str, float], dict[str, int]]:
    return ({key: item.initial_mastery for key, item in competencies.items()},
            {key: 0 for key in competencies})


def calculate_response_score(response_time: float, time_limit: float) -> float:
    if response_time < 0 or time_limit <= 0: raise ValueError("times must be valid positive values")
    ratio = response_time / time_limit
    if ratio <= .50: return 1.0
    if ratio <= .75: return .8
    if ratio <= 1.0: return .6
    return .3


def calculate_independence_score(hint_used: bool) -> float:
    if not isinstance(hint_used, bool): raise ValueError("hint_used must be boolean")
    return .5 if hint_used else 1.0


def update_multi_competence(
    scores: dict[str, float], repeated_errors: dict[str, int],
    affected: list[str], competence_accuracy: dict[str, bool],
    response_score: float, independence_score: float, learning_rate: float = .2,
) -> dict:
    """Update only affected competencies and their consecutive error counts."""
    new_scores, new_errors, observations = dict(scores), dict(repeated_errors), {}
    for competence_id in affected:
        if competence_id not in scores: raise ValueError(f"unknown competence: {competence_id}")
        correct = bool(competence_accuracy.get(competence_id, False))
        observation = calculate_observation_score(correct, response_score, independence_score)
        observations[competence_id] = observation
        new_scores[competence_id] = update_competence(scores[competence_id], observation, learning_rate)
        new_errors[competence_id] = 0 if correct else repeated_errors.get(competence_id, 0) + 1
    return {"competence_scores": new_scores, "repeated_errors": new_errors,
            "observation_scores": observations}


def competence_correctness(scenario, selected_ppe: set[str], ppe_items) -> dict[str, bool]:
    """Map exact PPE outcomes onto each scenario target competence."""
    required = set(scenario.required_ppe)
    exact = selected_ppe == required
    result = {}
    ppe_by_comp = {item.associated_competence_id: item.id for item in ppe_items.values()}
    for competence_id in scenario.target_competencies:
        if competence_id in ppe_by_comp:
            item = ppe_by_comp[competence_id]
            result[competence_id] = (item in selected_ppe) == (item in required)
        else:
            result[competence_id] = exact
    return result
