"""Accessible Plotly figures for scientific interpretation."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
LABELS={"static":"Static Baseline","score_adaptive":"Score-Based Adaptive","competence_adaptive":"Competence-Adaptive","proposed":"Proposed Framework"}
def metric_bar(aggregated,metric,title=None):
    df=pd.DataFrame(aggregated); df=df[df.metric==metric].copy(); df["Method"]=df.method.map(LABELS)
    fig=px.bar(df,x="Method",y="mean",error_y="standard_error",title=title or f"{metric} by method")
    fig.update_yaxes(title=f"Mean {metric}",rangemode="tozero"); return fig
def overall_comparison(figure5):
    df=pd.DataFrame(figure5); normalized=[]
    for metric,g in df.groupby("metric"):
        lo,hi=g["mean"].min(),g["mean"].max()
        for _,r in g.iterrows(): normalized.append({"Method":LABELS[r.method],"Metric":metric,"Normalized value":0 if hi==lo else (r["mean"]-lo)/(hi-lo)})
    return px.bar(pd.DataFrame(normalized),x="Method",y="Normalized value",color="Metric",barmode="group",title="Normalized multi-metric comparison")
def rwcs_development(rows):
    df=pd.DataFrame(rows); fig=go.Figure()
    if df.empty:
        fig.update_layout(title="RWCS development unavailable (episode logs disabled)",
            xaxis_title="Episode",yaxis_title="Mean RWCS",yaxis_range=[0,1])
        return fig
    for method,g in df.groupby("method"):
        fig.add_trace(go.Scatter(x=g.episode,y=g.mean_RWCS,mode="lines",name=LABELS[method],
          error_y={"type":"data","array":g.ci95_upper-g.mean_RWCS,"visible":True}))
    fig.update_layout(title="Risk-weighted competence development",xaxis_title="Episode",yaxis_title="Mean RWCS",yaxis_range=[0,1]); return fig
def target_achievement(run_rows):
    df=pd.DataFrame(run_rows).groupby("method",as_index=False).target_reached.mean(); df["method"]=df.method.map(LABELS)
    return px.bar(df,x="method",y="target_reached",title="Target achievement rate",labels={"method":"Method","target_reached":"Rate"},range_y=[0,1])
def profile_heatmap(run_rows,metric="RWCS"):
    df=pd.DataFrame(run_rows).pivot_table(index="trainee_profile",columns="method",values=metric,aggfunc="mean")
    return px.imshow(df,aspect="auto",text_auto=".3f",title=f"{metric}: profile × method")
def critical_error_comparison(aggregated): return metric_bar(aggregated,"CER","Critical error rate comparison")
def latency_comparison(aggregated): return metric_bar(aggregated,"mean_adaptation_latency_ms","Adaptation latency comparison (ms)")
