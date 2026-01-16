"""
Data Quality Agent - Streamlit Interface

A visual interface for analyzing dataset quality using AI-powered agents.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import tempfile
import json
from pathlib import Path
from datetime import datetime

from profiling import DataProfiler
from rag import RulesLoader
from agent import QualityAgent
from agent.quality_agent import Decision

# Page configuration
st.set_page_config(
    page_title="Data Quality Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .decision-accept {
        background-color: #28a745;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2em;
        font-weight: bold;
    }
    .decision-warning {
        background-color: #ffc107;
        color: black;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2em;
        font-weight: bold;
    }
    .decision-reject {
        background-color: #dc3545;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 2em;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    .issue-card {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
    }
    .issue-critical {
        background-color: #f8d7da;
        border-left-color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)


def load_rules():
    """Load quality rules."""
    rules_loader = RulesLoader("rules")
    rules_loader.load_rules()
    return rules_loader


def analyze_dataset(file_path: Path, use_v2: bool = False) -> tuple:
    """
    Analyze a dataset and return profile and report.

    Args:
        file_path: Path to the CSV file.
        use_v2: Whether to use V2 LLM-powered agent.

    Returns:
        Tuple of (profile, report).
    """
    # Profile the data
    profiler = DataProfiler(file_path)
    profile = profiler.generate_profile()

    # Load rules and create agent
    rules_loader = load_rules()

    if use_v2:
        try:
            from agent import LLMQualityAgent
            from rag import VectorRulesStore

            vector_store = VectorRulesStore()
            vector_store.index_rules(rules_loader.rules)

            agent = LLMQualityAgent(vector_store=vector_store)
        except Exception as e:
            st.error(f"V2 not available: {e}")
            st.info("Falling back to V1 (rule-based)")
            agent = QualityAgent(rules_loader)
    else:
        agent = QualityAgent(rules_loader)

    report = agent.analyze(profile)

    return profile, report


def render_decision_badge(decision: str):
    """Render a colored decision badge."""
    css_class = f"decision-{decision.lower()}"
    st.markdown(f'<div class="{css_class}">{decision}</div>', unsafe_allow_html=True)


def render_metrics(profile: dict, report):
    """Render dataset metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Rows", f"{profile['basic_stats']['row_count']:,}")
    with col2:
        st.metric("Columns", profile['basic_stats']['column_count'])
    with col3:
        st.metric("Issues Found", len(report.issues))
    with col4:
        # Calculate overall quality score
        if report.decision == "ACCEPT":
            score = 100
        elif report.decision == "WARNING":
            score = 70
        else:
            score = 30
        st.metric("Quality Score", f"{score}%")


def render_issues(report):
    """Render detected issues."""
    if not report.issues:
        st.success("No issues detected! Dataset passes all quality checks.")
        return

    for issue in report.issues:
        severity_color = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }.get(issue.severity.lower(), "⚪")

        with st.expander(f"{severity_color} {issue.type} - {issue.rule_reference}", expanded=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"**Severity:** {issue.severity.upper()}")
                if issue.column:
                    st.write(f"**Column:** `{issue.column}`")
            with col2:
                st.write(f"**Explanation:** {issue.explanation}")


def render_profile_details(profile: dict):
    """Render detailed profile information."""
    # Column types
    st.subheader("Column Types")
    col_data = []
    for col_name, col_info in profile["column_types"].items():
        col_data.append({
            "Column": col_name,
            "Pandas Type": col_info.get("pandas_dtype", "N/A"),
            "Semantic Type": col_info.get("semantic_type", "N/A")
        })
    if col_data:
        st.dataframe(pd.DataFrame(col_data), use_container_width=True)

    # Missing values
    st.subheader("Missing Values")
    missing_data = []
    for col_name, col_info in profile["missing_values"].items():
        pct = col_info.get("missing_percentage", 0)
        if pct > 0:
            missing_data.append({
                "Column": col_name,
                "Missing Count": col_info.get("missing_count", 0),
                "Missing %": f"{pct:.1f}%"
            })
    if missing_data:
        st.dataframe(pd.DataFrame(missing_data), use_container_width=True)
    else:
        st.info("No missing values detected.")

    # Outliers
    if profile.get("outliers"):
        st.subheader("Outliers Detected")
        outlier_data = []
        for col_name, col_info in profile["outliers"].items():
            outlier_data.append({
                "Column": col_name,
                "Outlier Count": col_info.get("outlier_count", 0),
                "Outlier %": f"{col_info.get('outlier_percentage', 0):.1f}%"
            })
        if outlier_data:
            st.dataframe(pd.DataFrame(outlier_data), use_container_width=True)

    # Negative values
    if profile.get("negative_values"):
        st.subheader("Negative Values")
        neg_data = []
        for col_name, col_info in profile["negative_values"].items():
            neg_data.append({
                "Column": col_name,
                "Negative Count": col_info.get("negative_count", 0),
                "Negative %": f"{col_info.get('negative_percentage', 0):.1f}%"
            })
        if neg_data:
            st.dataframe(pd.DataFrame(neg_data), use_container_width=True)


def render_download_buttons(report, profile):
    """Render download buttons for reports."""
    col1, col2 = st.columns(2)

    # JSON download
    with col1:
        report_dict = report.to_dict()
        report_dict["metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "agent_version": "V1 (rule-based)"
        }
        json_str = json.dumps(report_dict, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download JSON Report",
            data=json_str,
            file_name=f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

    # HTML download
    with col2:
        html_content = generate_html_report(report, profile)
        st.download_button(
            label="📥 Download HTML Report",
            data=html_content,
            file_name=f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )


def generate_html_report(report, profile) -> str:
    """Generate HTML report content."""
    decision_colors = {
        "ACCEPT": "#28a745",
        "WARNING": "#ffc107",
        "REJECT": "#dc3545"
    }
    color = decision_colors.get(report.decision, "#6c757d")

    issues_html = ""
    if report.issues:
        for issue in report.issues:
            issues_html += f"""
            <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid {color}; border-radius: 0 8px 8px 0;">
                <strong>{issue.type}</strong> ({issue.rule_reference})<br>
                <small>Severity: {issue.severity.upper()}</small><br>
                {f'<small>Column: {issue.column}</small><br>' if issue.column else ''}
                <p>{issue.explanation}</p>
            </div>
            """
    else:
        issues_html = '<p style="color: #28a745;">No issues detected.</p>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Data Quality Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; padding: 20px; }}
            .decision {{ background: {color}; color: white; padding: 20px; border-radius: 10px; font-size: 2em; text-align: center; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Data Quality Report</h1>
            <div class="decision">{report.decision}</div>
        </div>
        <p><strong>Summary:</strong> {report.summary}</p>
        <div class="stats">
            <div class="stat"><h3>{profile['basic_stats']['row_count']:,}</h3><p>Rows</p></div>
            <div class="stat"><h3>{profile['basic_stats']['column_count']}</h3><p>Columns</p></div>
            <div class="stat"><h3>{len(report.issues)}</h3><p>Issues</p></div>
        </div>
        <h2>Issues</h2>
        {issues_html}
        <footer style="text-align: center; margin-top: 30px; color: #6c757d;">
            Generated by Data Quality Agent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </footer>
    </body>
    </html>
    """


def main():
    """Main Streamlit application."""

    # Header
    st.title("🔍 Data Quality Agent")
    st.markdown("*AI-powered data quality assessment for tabular datasets*")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Agent version selection
        agent_version = st.radio(
            "Agent Version",
            ["V1 - Rule-based (Fast)", "V2 - LLM-powered (Claude)"],
            help="V1 uses hard-coded rules. V2 uses Claude for intelligent reasoning."
        )
        use_v2 = "V2" in agent_version

        if use_v2:
            st.warning("⚠️ V2 requires ANTHROPIC_API_KEY in .env file")

        st.divider()

        # Sample datasets
        st.header("📁 Sample Datasets")
        sample_files = list(Path("data/test").glob("*.csv")) if Path("data/test").exists() else []

        if sample_files:
            selected_sample = st.selectbox(
                "Load a sample dataset",
                ["None"] + [f.name for f in sample_files]
            )
        else:
            selected_sample = "None"
            st.info("No sample datasets found in data/test/")

        st.divider()

        # About section
        st.header("ℹ️ About")
        st.markdown("""
        This tool analyzes CSV datasets for quality issues:
        - Missing values
        - Outliers (IQR method)
        - Negative values
        - Empty datasets

        **Author:** Killian PERZO
        """)

    # Main content
    st.header("📤 Upload Dataset")

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Upload a CSV file to analyze its quality"
    )

    # Handle sample dataset selection
    file_to_analyze = None

    if uploaded_file is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            file_to_analyze = Path(tmp.name)
        st.success(f"Uploaded: {uploaded_file.name}")

    elif selected_sample != "None":
        file_to_analyze = Path("data/test") / selected_sample
        st.info(f"Using sample dataset: {selected_sample}")

    # Analyze button
    if file_to_analyze:
        if st.button("🚀 Analyze Dataset", type="primary", use_container_width=True):
            with st.spinner("Analyzing dataset..."):
                try:
                    profile, report = analyze_dataset(file_to_analyze, use_v2)

                    # Store results in session state
                    st.session_state.profile = profile
                    st.session_state.report = report
                    st.session_state.analyzed = True

                except Exception as e:
                    st.error(f"Error analyzing dataset: {e}")
                    st.session_state.analyzed = False

    # Display results
    if st.session_state.get("analyzed", False):
        profile = st.session_state.profile
        report = st.session_state.report

        st.divider()

        # Decision
        st.header("📊 Analysis Results")

        col1, col2 = st.columns([1, 2])

        with col1:
            render_decision_badge(report.decision)

        with col2:
            st.markdown(f"**Summary:** {report.summary}")

        st.divider()

        # Metrics
        render_metrics(profile, report)

        st.divider()

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["🚨 Issues", "📈 Profile Details", "📥 Export"])

        with tab1:
            render_issues(report)

        with tab2:
            render_profile_details(profile)

        with tab3:
            st.subheader("Download Reports")
            render_download_buttons(report, profile)

    else:
        # Show placeholder when no file is analyzed
        st.info("👆 Upload a CSV file or select a sample dataset to begin analysis")

        # Show example of what the tool does
        with st.expander("ℹ️ What does this tool check?"):
            st.markdown("""
            | Check | Description | Threshold |
            |-------|-------------|-----------|
            | **Missing Values** | Detects columns with null/empty values | WARNING > 20%, REJECT > 40% |
            | **Empty Dataset** | Checks if dataset has zero rows | REJECT |
            | **Outliers** | Identifies extreme values using IQR | WARNING > 5% |
            | **Negative Values** | Finds impossible negative values | WARNING |
            """)


if __name__ == "__main__":
    main()
