import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
import base64
from fpdf import FPDF

def load_results(file_path: str) -> dict:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return json.load(f)

def create_metrics_df(results: dict) -> pd.DataFrame:
    metrics = results['metadata']['avg_scores']['avg_scores']
    data = [
        {
            'Metric': metric,
            'Average Score': details['average'],
            'Standard Deviation': details['std_dev'],
            'Success Rate': details['success_rate'],
            'Total Samples': details['total_samples']
        }
        for metric, details in metrics.items()
        if metric != 'AVG_SCORE (excl. custom metrics)'
    ]
    return pd.DataFrame(data)

def export_report(results: dict, metrics_df: pd.DataFrame) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'LLM Evaluation Report', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Key Metrics', 0, 1, 'L')
    pdf.set_font('Arial', '', 12)
    metrics = [
        f"Number of Test Cases: {results['metadata']['num_test_cases']}",
        f"Average Score: {results['metadata']['avg_scores']['avg_scores']['AVG_SCORE (excl. custom metrics)']['average']:.2f}",
        f"Success Rate: {results['metadata']['avg_scores']['avg_scores']['AVG_SCORE (excl. custom metrics)']['success_rate']:.2%}",
        f"Evaluation Timestamp: {results['metadata']['timestamp']}"
    ]
    for metric in metrics:
        pdf.cell(0, 10, metric, 0, 1, 'L')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Detailed Metrics', 0, 1, 'L')
    pdf.set_font('Arial', 'B', 10)
    col_widths = [50, 35, 35, 35, 35]
    headers = ['Metric', 'Avg Score', 'Std Dev', 'Success Rate', 'Total Samples']
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 10, header, 1)
    pdf.ln()
    pdf.set_font('Arial', '', 10)
    for _, row in metrics_df.iterrows():
        pdf.cell(col_widths[0], 10, str(row['Metric'])[:30], 1)
        pdf.cell(col_widths[1], 10, f"{row['Average Score']:.2f}", 1)
        pdf.cell(col_widths[2], 10, f"{row['Standard Deviation']:.2f}", 1)
        pdf.cell(col_widths[3], 10, f"{row['Success Rate']:.2%}", 1)
        pdf.cell(col_widths[4], 10, f"{row['Total Samples']:,}", 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

def main() -> None:
    st.set_page_config(page_title="LLM Evaluation Dashboard", layout="wide")
    with st.sidebar:
        st.title("📊 Configuration")
        st.markdown("---")
        uploaded_files = st.file_uploader(
            "Drop JSON results files here",
            type=['json'],
            accept_multiple_files=True,
            help="Upload one or more evaluation result files"
        )
        if not uploaded_files:
            st.info("👆 Upload your evaluation results to begin")
            return
        selected_file = st.selectbox(
            "Select result file to view",
            options=uploaded_files,
            format_func=lambda x: x.name
        ) if len(uploaded_files) > 1 else uploaded_files[0]
        results = json.load(selected_file)
        df = create_metrics_df(results)
        st.subheader("🎯 Metric Filters")
        selected_metrics = st.multiselect(
            "Select metrics to display",
            options=df['Metric'].unique(),
            default=df['Metric'].unique(),
            help="Choose which metrics to show in the dashboard"
        )
    if uploaded_files:
        st.title("LLM Evaluation Metrics Dashboard")
        st.markdown(f"*Analyzing results from: **{selected_file.name}***")
        filtered_df = df[df['Metric'].isin(selected_metrics)]
        st.markdown("### 📈 Key Metrics")
        metrics_cols = st.columns(4)
        metrics_cols[0].metric(
            "Number of Test Cases",
            value=results['metadata']['num_test_cases'],
            help="Total number of test cases evaluated"
        )
        avg_score = results['metadata']['avg_scores']['avg_scores']['AVG_SCORE (excl. custom metrics)']
        metrics_cols[1].metric(
            "Overall Average Score",
            value=f"{avg_score['average']:.2f}",
            help="Average score across all metrics"
        )
        metrics_cols[2].metric(
            "Overall Success Rate",
            value=f"{avg_score['success_rate']:.2%}",
            help="Percentage of successful test cases"
        )
        metrics_cols[3].metric(
            "Evaluation Timestamp",
            value=results['metadata']['timestamp'],
            help="Timestamp of the evaluation"
        )
        st.markdown("### 📊 Metrics Comparison")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Average Score',
            x=filtered_df['Metric'],
            y=filtered_df['Average Score'],
            error_y=dict(type='data', array=filtered_df['Standard Deviation'], visible=True),
            marker_color='#2ecc71'
        ))
        fig.add_trace(go.Scatter(
            name='Success Rate',
            x=filtered_df['Metric'],
            y=filtered_df['Success Rate'],
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='#e74c3c'),
            marker=dict(size=8)
        ))
        fig.update_layout(
            yaxis=dict(title='Average Score', range=[0, 1], gridcolor='#f0f0f0'),
            yaxis2=dict(title='Success Rate', range=[0, 1], overlaying='y', side='right'),
            barmode='group',
            height=500,
            template='plotly_white',
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### 📋 Detailed Analysis")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(
                filtered_df.style.format({
                    'Average Score': '{:.2f}',
                    'Standard Deviation': '{:.2f}',
                    'Success Rate': '{:.2%}',
                    'Total Samples': '{:,}'
                }),
                hide_index=True,
                height=250,
                use_container_width=True
            )
        with col2:
            test_results = pd.DataFrame(results['test_results'])
            success_rate = test_results['success'].mean()
            pie_fig = px.pie(
                values=[success_rate, 1 - success_rate],
                names=['Success', 'Failure'],
                color_discrete_sequence=['#2ecc71', '#e74c3c'],
                hole=0.4
            )
            pie_fig.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=40, b=20),
                height=250
            )
            pie_fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(pie_fig, use_container_width=True)
        st.markdown("---")
        export_cols = st.columns([1, 2, 1])
        with export_cols[1]:
            if st.button("📊 Generate PDF Report", use_container_width=True):
                with st.spinner("Generating PDF report..."):
                    try:
                        pdf_data = export_report(results, df)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        b64_pdf = base64.b64encode(pdf_data).decode('utf-8')
                        pdf_display = f'<a href="data:application/pdf;base64,{b64_pdf}" download="llm_evaluation_report_{timestamp}.pdf">⬇️ Download PDF Report</a>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                        st.success("✅ PDF report generated successfully!")
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")

if __name__ == "__main__":
    main()
