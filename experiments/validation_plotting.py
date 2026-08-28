"""Plot-ready data transformations without Streamlit dependencies."""
def metric_plot_data(summary_rows,metric):
    return [row for row in summary_rows if row.get("metric")==metric]
