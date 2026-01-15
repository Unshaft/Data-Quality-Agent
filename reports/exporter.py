"""
Report Exporter module.
Generates quality reports in various formats (JSON, HTML).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.quality_agent import QualityReport

logger = logging.getLogger(__name__)


class ReportExporter:
    """
    Exports quality reports to various formats.

    Supports:
    - JSON: Machine-readable format for integration
    - HTML: Human-readable format for sharing
    """

    def __init__(self, output_dir: str | Path = "reports"):
        """
        Initialize the exporter.

        Args:
            output_dir: Directory to save reports.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(
        self,
        report: QualityReport,
        filename: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Export report to JSON format.

        Args:
            report: QualityReport to export.
            filename: Output filename (auto-generated if None).
            metadata: Additional metadata to include.

        Returns:
            Path to the exported file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.json"

        output_path = self.output_dir / filename

        report_dict = report.to_dict()
        report_dict["metadata"] = metadata or {}
        report_dict["metadata"]["exported_at"] = datetime.now().isoformat()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON report exported to: {output_path}")
        return output_path

    def export_html(
        self,
        report: QualityReport,
        filename: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Export report to HTML format.

        Args:
            report: QualityReport to export.
            filename: Output filename (auto-generated if None).
            metadata: Additional metadata to include.

        Returns:
            Path to the exported file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.html"

        output_path = self.output_dir / filename
        metadata = metadata or {}

        # Generate HTML content
        html_content = self._generate_html(report, metadata)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML report exported to: {output_path}")
        return output_path

    def _generate_html(
        self,
        report: QualityReport,
        metadata: dict[str, Any],
    ) -> str:
        """
        Generate HTML content for the report.

        Args:
            report: QualityReport to render.
            metadata: Report metadata.

        Returns:
            HTML string.
        """
        # Determine color based on decision
        decision_colors = {
            "ACCEPT": "#28a745",
            "WARNING": "#ffc107",
            "REJECT": "#dc3545",
        }
        decision_color = decision_colors.get(report.decision, "#6c757d")

        # Generate issues HTML
        issues_html = ""
        if report.issues:
            issues_items = ""
            for issue in report.issues:
                severity_colors = {
                    "low": "#28a745",
                    "medium": "#ffc107",
                    "high": "#fd7e14",
                    "critical": "#dc3545",
                }
                severity_color = severity_colors.get(issue.severity.lower(), "#6c757d")

                column_info = f"<br><strong>Column:</strong> {issue.column}" if issue.column else ""

                issues_items += f"""
                <div class="issue">
                    <div class="issue-header">
                        <span class="issue-type">{issue.type}</span>
                        <span class="issue-severity" style="background-color: {severity_color};">{issue.severity.upper()}</span>
                    </div>
                    <p><strong>Rule:</strong> {issue.rule_reference}{column_info}</p>
                    <p>{issue.explanation}</p>
                </div>
                """

            issues_html = f"""
            <section class="issues">
                <h2>Issues Detected ({len(report.issues)})</h2>
                {issues_items}
            </section>
            """
        else:
            issues_html = """
            <section class="issues">
                <h2>Issues Detected</h2>
                <p class="no-issues">No issues detected. Dataset passes all quality checks.</p>
            </section>
            """

        # Generate metadata HTML
        metadata_html = ""
        if metadata:
            metadata_items = "".join(
                f"<tr><td>{k}</td><td>{v}</td></tr>"
                for k, v in metadata.items()
            )
            metadata_html = f"""
            <section class="metadata">
                <h2>Report Metadata</h2>
                <table>
                    {metadata_items}
                </table>
            </section>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Quality Report</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        header h1 {{
            font-size: 1.8rem;
            margin-bottom: 10px;
        }}
        .decision-badge {{
            display: inline-block;
            padding: 10px 30px;
            border-radius: 25px;
            font-size: 1.5rem;
            font-weight: bold;
            color: white;
            background-color: {decision_color};
            margin: 15px 0;
        }}
        .summary {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        .summary p {{
            font-size: 1.1rem;
        }}
        .stats {{
            padding: 20px 30px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            border-bottom: 1px solid #dee2e6;
        }}
        .stat-box {{
            flex: 1;
            min-width: 150px;
            padding: 15px;
            background: #e9ecef;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-box .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #495057;
        }}
        .stat-box .label {{
            font-size: 0.9rem;
            color: #6c757d;
        }}
        .issues {{
            padding: 20px 30px;
        }}
        .issues h2 {{
            margin-bottom: 15px;
            color: #495057;
        }}
        .issue {{
            background: #f8f9fa;
            border-left: 4px solid #6c757d;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 0 8px 8px 0;
        }}
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .issue-type {{
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .issue-severity {{
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            color: white;
            font-weight: bold;
        }}
        .no-issues {{
            color: #28a745;
            font-style: italic;
            padding: 20px;
            text-align: center;
            background: #d4edda;
            border-radius: 8px;
        }}
        .metadata {{
            padding: 20px 30px;
            border-top: 1px solid #dee2e6;
        }}
        .metadata h2 {{
            margin-bottom: 15px;
            color: #495057;
        }}
        .metadata table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .metadata td {{
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }}
        .metadata td:first-child {{
            font-weight: bold;
            width: 200px;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Data Quality Report</h1>
            <div class="decision-badge">{report.decision}</div>
        </header>

        <section class="summary">
            <p>{report.summary}</p>
        </section>

        <section class="stats">
            <div class="stat-box">
                <div class="value">{report.stats.get('row_count', 0):,}</div>
                <div class="label">Rows</div>
            </div>
            <div class="stat-box">
                <div class="value">{report.stats.get('column_count', 0)}</div>
                <div class="label">Columns</div>
            </div>
            <div class="stat-box">
                <div class="value">{report.stats.get('issues_count', 0)}</div>
                <div class="label">Issues</div>
            </div>
        </section>

        {issues_html}

        {metadata_html}

        <footer>
            Generated by Data Quality Agent on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </footer>
    </div>
</body>
</html>"""

        return html

    def export_batch_summary(
        self,
        reports: list[tuple[str, QualityReport]],
        filename: str = "batch_summary.html",
    ) -> Path:
        """
        Export a summary of multiple reports.

        Args:
            reports: List of (filename, report) tuples.
            filename: Output filename.

        Returns:
            Path to the exported file.
        """
        output_path = self.output_dir / filename

        # Count by decision
        counts = {"ACCEPT": 0, "WARNING": 0, "REJECT": 0}
        for _, report in reports:
            counts[report.decision] = counts.get(report.decision, 0) + 1

        # Generate rows
        rows_html = ""
        for file_path, report in reports:
            decision_colors = {
                "ACCEPT": "#28a745",
                "WARNING": "#ffc107",
                "REJECT": "#dc3545",
            }
            color = decision_colors.get(report.decision, "#6c757d")
            rows_html += f"""
            <tr>
                <td>{file_path}</td>
                <td style="color: {color}; font-weight: bold;">{report.decision}</td>
                <td>{report.stats.get('row_count', 0):,}</td>
                <td>{len(report.issues)}</td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch Analysis Summary</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .summary-stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            flex: 1;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            color: white;
        }}
        .stat-box.accept {{ background: #28a745; }}
        .stat-box.warning {{ background: #ffc107; color: #333; }}
        .stat-box.reject {{ background: #dc3545; }}
        .stat-box .count {{ font-size: 2.5rem; font-weight: bold; }}
        .stat-box .label {{ font-size: 0.9rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        tr:hover {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Batch Analysis Summary</h1>

        <div class="summary-stats">
            <div class="stat-box accept">
                <div class="count">{counts.get('ACCEPT', 0)}</div>
                <div class="label">ACCEPT</div>
            </div>
            <div class="stat-box warning">
                <div class="count">{counts.get('WARNING', 0)}</div>
                <div class="label">WARNING</div>
            </div>
            <div class="stat-box reject">
                <div class="count">{counts.get('REJECT', 0)}</div>
                <div class="label">REJECT</div>
            </div>
        </div>

        <h2>Dataset Results ({len(reports)} files)</h2>
        <table>
            <thead>
                <tr>
                    <th>File</th>
                    <th>Decision</th>
                    <th>Rows</th>
                    <th>Issues</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <p style="margin-top: 30px; color: #6c757d; text-align: center;">
            Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </p>
    </div>
</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Batch summary exported to: {output_path}")
        return output_path
