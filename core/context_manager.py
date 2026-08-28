"""Single shared Streamlit session-state lifecycle."""
import time, uuid
from .learner_model import initialize_learner
from .scenario_manager import select_initial_scenario

def initialize_session(state, data):
    scores, errors = initialize_learner(data["competencies"])
    defaults = {"session_id":str(uuid.uuid4()), "trainee_id":"Anonymous Trainee",
        "episode":1, "current_scenario_id":select_initial_scenario(data["scenarios"]),
        "next_scenario_id":None, "current_difficulty":1, "competence_scores":scores,
        "repeated_errors":errors, "scenario_history":[], "decision_traces":[],
        "hint_used":False, "submission_processed":False, "scenario_start_time":time.time(),
        "session_status":"active", "last_trace":None, "ppe_selection":[],
        "assistance":"limited_visual_guidance", "distractor_level":"low"}
    for key, value in defaults.items():
        if key not in state: state[key] = value

def reset_session(state, data):
    for key in list(state.keys()): del state[key]
    initialize_session(state, data)
