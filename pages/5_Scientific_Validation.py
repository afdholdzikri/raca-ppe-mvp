"""Version 4 scientific-validation workbench."""
import json
import streamlit as st
from experiments.ablation_engine import run_ablation
from experiments.domain_adapter import DOMAIN_REGISTRY,validate_all_domains
from experiments.replication_engine import run_cross_domain_replication
from experiments.sensitivity_config import SENSITIVITY_GRIDS
from experiments.sensitivity_engine import run_sensitivity
from experiments.statistical_analysis import compare_paired_rows
from experiments.trace_audit import run_trace_audit
from experiments.validation_export import serialize_outputs

st.set_page_config(page_title="Scientific Validation",page_icon="🔬",layout="wide")
st.title("Version 4 Scientific Validation")
st.warning("All outcomes are synthetic simulation results and are not evidence of human learning or accident reduction.")
for key in ("v4_ablation","v4_sensitivity","v4_replication","v4_audit"):
    st.session_state.setdefault(key,None)

tabs=st.tabs(["Prerequisite Audit","Ablation Study","Sensitivity Analysis",
 "Decision-Trace Audit","Cross-Domain Replication","Statistical Summary","Downloads"])

with tabs[0]:
    st.subheader("Prerequisite Audit")
    if st.button("Validate domain prerequisites"):
        try:
            data=validate_all_domains()
            st.session_state.v4_prerequisite={name:{"scenarios":len(value["scenarios"]),"valid":True} for name,value in data.items()}
        except ValueError as exc:st.error(f"Prerequisite failed: {exc}")
    if st.session_state.get("v4_prerequisite"):st.json(st.session_state.v4_prerequisite)
    else:st.info("Run the prerequisite audit to display domain validation.")

with tabs[1]:
    st.subheader("Feature-Flag Ablation")
    if st.button("Run small ablation"):
        with st.spinner("Running paired ablations..."):
            st.session_state.v4_ablation=run_ablation(5,2,42,["T1","T2"])
    if st.session_state.v4_ablation:st.dataframe(st.session_state.v4_ablation["summary"],use_container_width=True)
    else:st.info("No ablation result is loaded.")

with tabs[2]:
    st.subheader("One-Factor-at-a-Time Sensitivity")
    parameter=st.selectbox("Parameter",list(SENSITIVITY_GRIDS),key="v4_sensitivity_parameter")
    if st.button("Run small sensitivity"):
        with st.spinner("Running sensitivity analysis..."):
            st.session_state.v4_sensitivity=run_sensitivity(parameter,None,5,2,42,["T1","T2"])
    if st.session_state.v4_sensitivity:
        st.dataframe(st.session_state.v4_sensitivity["summary"],use_container_width=True)
        st.dataframe(st.session_state.v4_sensitivity["variation"],use_container_width=True)
    else:st.info("No sensitivity result is loaded.")

with tabs[3]:
    st.subheader("Decision-Trace Audit")
    if st.button("Audit current replication traces",disabled=not bool(st.session_state.v4_replication)):
        st.session_state.v4_audit=run_trace_audit(st.session_state.v4_replication["cycle_results"])
    if st.session_state.v4_audit:st.json(st.session_state.v4_audit["summary"])
    else:st.info("Run cross-domain replication before auditing its traces.")

with tabs[4]:
    st.subheader("Cross-Domain Replication")
    domains=st.multiselect("Domains",list(DOMAIN_REGISTRY),default=list(DOMAIN_REGISTRY),key="v4_domains")
    if st.button("Run small replication",disabled=not domains):
        with st.spinner("Running domain replication..."):
            st.session_state.v4_replication=run_cross_domain_replication(domains,["T1","T2"],5,2,42)
    if st.session_state.v4_replication:
        st.dataframe(st.session_state.v4_replication["summary"],use_container_width=True)
    else:st.info("No replication result is loaded.")

with tabs[5]:
    st.subheader("Synthetic Statistical Summary")
    if st.session_state.v4_ablation:
        rows=st.session_state.v4_ablation["run_results"]
        comparisons=compare_paired_rows(rows,"ablation","FULL",
          ["A1_NO_RISK_WEIGHTING","A2_NO_DYNAMIC_CONTEXT","A3_NO_ERROR_HISTORY",
           "A4_NO_ADAPTIVE_ASSISTANCE","A5_NO_DECISION_TRACE"],"final_RWCS")
        st.dataframe(comparisons,use_container_width=True)
    else:st.info("Run the ablation study to calculate paired comparisons.")

with tabs[6]:
    st.subheader("Downloads")
    available={"ablation":st.session_state.v4_ablation,"sensitivity":st.session_state.v4_sensitivity,
      "replication":st.session_state.v4_replication,"trace_audit":st.session_state.v4_audit}
    shown=False
    for label,result in available.items():
        if not result:continue
        shown=True
        for name,value in serialize_outputs(result["files"]).items():
            st.download_button(f"{label}: {name}",value,file_name=name,key=f"download_{label}_{name}")
    if not shown:st.info("Completed validation outputs will appear here.")
