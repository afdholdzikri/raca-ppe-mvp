"""One-factor-at-a-time sensitivity grids and base configuration."""
BASE_VALUES={"learning_rate":.20,"repetition_weight":.50,"target_mastery":.80,"critical_risk_threshold":.75}
SENSITIVITY_GRIDS={
 "learning_rate":[.05,.10,.20,.30,.40],
 "repetition_weight":[.00,.25,.50,.75,1.00],
 "target_mastery":[.70,.75,.80,.85,.90],
 "critical_risk_threshold":[.60,.70,.75,.80,.90],
}

def ofat_configuration(parameter,value):
    if parameter not in SENSITIVITY_GRIDS:raise ValueError(f"unsupported sensitivity parameter {parameter!r}")
    config=dict(BASE_VALUES);config[parameter]=float(value);return config
