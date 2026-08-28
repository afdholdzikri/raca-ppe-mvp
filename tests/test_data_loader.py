import json, shutil
import pytest
from core.data_loader import DATA_DIR, load_all_data

def test_all_data_loads_and_references_validate():
    d=load_all_data(); assert len(d["ppe"])==6; assert len(d["hazards"])==9
    assert len(d["competencies"])>=10; assert len(d["scenarios"])==6

def test_invalid_reference_is_meaningful(tmp_path):
    for name in ["ppe.json","hazards.json","competencies.json","scenarios.json","adaptation_rules.json"]:
        shutil.copy(DATA_DIR/name,tmp_path/name)
    scenarios=json.loads((tmp_path/"scenarios.json").read_text())
    scenarios[0]["hazards"]=["unknown"]
    (tmp_path/"scenarios.json").write_text(json.dumps(scenarios))
    with pytest.raises(ValueError,match="unknown hazard"):
        load_all_data(tmp_path)

def test_invalid_ppe_competence_reference_is_meaningful(tmp_path):
    for name in ["ppe.json","hazards.json","competencies.json","scenarios.json","adaptation_rules.json"]:
        shutil.copy(DATA_DIR/name,tmp_path/name)
    ppe=json.loads((tmp_path/"ppe.json").read_text())
    ppe[0]["associated_competence_id"]="unknown"
    (tmp_path/"ppe.json").write_text(json.dumps(ppe))
    with pytest.raises(ValueError,match="PPE helmet references unknown competence"):
        load_all_data(tmp_path)
