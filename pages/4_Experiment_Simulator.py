"""Version 3 controlled synthetic-participant experiment UI."""
from pathlib import Path
import pandas as pd
import streamlit as st
from experiments.experiment_config import ExperimentConfig,VALID_METHODS,VALID_PROFILES
from experiments.simulation_engine import run_batch_experiments
from experiments.export_manager import build_exports,save_exports
from experiments.plotting import (overall_comparison,rwcs_development,
    critical_error_comparison,target_achievement,latency_comparison,profile_heatmap)
from experiments.ui_state import (clear_experiment_state,
    initialize_experiment_state,store_completed_experiment)

st.set_page_config(page_title="Experiment Simulator",page_icon="🧪",layout="wide")
st.title("Version 3 — Research Experiment Engine")
st.warning("This synthetic-participant simulation is computational proof-of-work and mechanistic validation only. It does not establish human learning, behavioural transfer, or accident reduction.")
initialize_experiment_state(st.session_state)

with st.form("experiment_config_widget"):
    methods=st.multiselect("Methods",VALID_METHODS,default=list(VALID_METHODS),
        key="experiment_methods_widget")
    profiles=st.multiselect("Synthetic trainee profiles",VALID_PROFILES,
        default=list(VALID_PROFILES),key="experiment_profiles_widget")
    c1,c2,c3=st.columns(3)
    episodes=c1.number_input("Episodes per run",1,100,30,key="experiment_episodes_widget")
    repetitions=c2.number_input("Repetitions",1,100,30,key="experiment_repetitions_widget")
    seed=c3.number_input("Random seed",value=42,step=1,key="experiment_seed_widget")
    c4,c5,c6=st.columns(3)
    target=c4.slider("Target mastery",0.0,1.0,.8,.01,key="experiment_target_widget")
    learning=c5.slider("Learning rate",.01,1.0,.2,.01,
        key="experiment_learning_rate_widget")
    repetition_weight=c6.slider("Repetition weight",0.0,2.0,.5,.05,
        key="experiment_repetition_weight_widget")
    logs=st.checkbox("Save episode logs",True,key="experiment_save_logs_widget")
    traces=st.checkbox("Save decision traces",True,key="experiment_save_traces_widget")
    submitted=st.form_submit_button("Run Experiment",type="primary",disabled=st.session_state.experiment_running)
estimated=len(methods)*len(profiles)*repetitions*episodes
st.metric("Maximum episode evaluations",estimated)
if estimated>20000: st.warning("Large experiment: local execution may take several minutes.")

if submitted:
    st.session_state.experiment_running=True
    progress=st.progress(0); status=st.empty()
    try:
        result=None
        try:
            config=ExperimentConfig(methods=methods,trainee_profiles=profiles,
              episodes_per_run=int(episodes),repetitions=int(repetitions),
              random_seed=int(seed),target_mastery=target,
              learning_rate=learning,repetition_weight=repetition_weight,
              save_episode_logs=logs,save_decision_traces=traces)
            result=run_batch_experiments(config,
              lambda d,t:(progress.progress(d/t),status.write(f"Run {d} of {t}")))
        except Exception as exc:
            # Only validation, simulation, or aggregation failures use this label.
            st.error(f"Experiment failed: {exc}")
        if result is not None:
            # Commit successful scientific output before optional export operations.
            store_completed_experiment(st.session_state,config.to_dict(),result)
            try:
                exports=build_exports(result,config,
                    Path(__file__).resolve().parent.parent/"data")
                saved=save_exports(exports,result["experiment_id"])
                st.session_state.experiment_exports=exports
                st.session_state.experiment_saved_path=str(saved) if saved else None
                if saved is None:
                    st.session_state.experiment_export_warning=(
                        "Experiment completed, but one or more files could not be exported."
                    )
            except Exception:
                st.session_state.experiment_exports={}
                st.session_state.experiment_saved_path=None
                st.session_state.experiment_export_warning=(
                    "Experiment completed, but one or more files could not be exported."
                )
            progress.progress(1.0); status.success("Experiment complete")
    finally:
        st.session_state.experiment_running=False

if st.session_state.get("experiment_export_warning"):
    st.warning(st.session_state.experiment_export_warning)

result=st.session_state.get("experiment_results")
if result:
    runs=pd.DataFrame(result["run_rows"])
    cards=st.columns(4)
    cards[0].metric("Runs",len(runs)); cards[1].metric("Episodes",len(result["episode_rows"]))
    cards[2].metric("Elapsed (s)",result["elapsed_seconds"]); cards[3].metric("Target achievement",f"{runs.target_reached.mean():.1%}")
    st.caption("Synthetic outcomes are not human-subject validation. All displayed values are generated by the current archived simulation.")
    st.subheader("Overall Performance Comparison"); st.dataframe(result["overall_table"],use_container_width=True,hide_index=True)
    st.plotly_chart(overall_comparison(result["figure5_data"]),use_container_width=True)
    st.plotly_chart(rwcs_development(result["figure6_data"]),use_container_width=True)
    c1,c2=st.columns(2); c1.plotly_chart(critical_error_comparison(result["aggregated"]),use_container_width=True)
    c2.plotly_chart(target_achievement(result["run_rows"]),use_container_width=True)
    st.plotly_chart(latency_comparison(result["aggregated"]),use_container_width=True)
    profile=st.selectbox("Profile-level analysis",
        ["All"]+sorted(runs.trainee_profile.unique()),
        key="experiment_profile_filter_widget")
    filtered=result["run_rows"] if profile=="All" else [r for r in result["run_rows"] if r["trainee_profile"]==profile]
    st.plotly_chart(profile_heatmap(filtered),use_container_width=True)
    st.subheader("Downloads")
    for name,value in st.session_state.get("experiment_exports",{}).items():
        mime="application/zip" if name.endswith(".zip") else "text/csv" if name.endswith(".csv") else "application/json" if name.endswith((".json",".jsonl")) else "text/markdown"
        st.download_button(f"Download {name}",value,name,mime)

def reset_experiment():
    # Button callbacks run before widget reconstruction, so widget-owned values
    # can be deleted safely here.
    clear_experiment_state(st.session_state,clear_widget_values=True)
st.button("Reset Experiment",on_click=reset_experiment)
