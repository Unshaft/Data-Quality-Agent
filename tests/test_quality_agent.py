"""
Unit tests for the QualityAgent module (V1 rule-based agent).
"""

import pytest

from agent.quality_agent import QualityAgent, QualityReport, Decision, Severity, Issue
from rag.rules_loader import RulesLoader


class TestQualityAgent:
    """Tests for QualityAgent class."""

    @pytest.fixture
    def rules_dir(self, tmp_path):
        """Create a temporary rules directory with test rules."""
        rules_content = """# Quality Rules

## DQ-01 - Missing values
**Severity**: WARNING/CRITICAL
**Description**: Detect columns with missing values.
**Threshold**: WARNING if > 20%, CRITICAL if > 40%

## DQ-02 - Empty dataset
**Severity**: CRITICAL
**Description**: Dataset has no rows.
**Action**: REJECT immediately

## DQ-04 - Negative values
**Severity**: WARNING
**Description**: Negative values in columns that should be positive.

## DQ-05 - Outliers
**Severity**: WARNING
**Description**: Extreme outliers in numeric columns.
**Threshold**: WARNING if > 5% outliers
"""
        rules_file = tmp_path / "test_rules.md"
        rules_file.write_text(rules_content, encoding="utf-8")
        return str(tmp_path)

    @pytest.fixture
    def rules_loader(self, rules_dir):
        """Create a RulesLoader with test rules."""
        loader = RulesLoader(rules_dir)
        loader.load_rules()
        return loader

    @pytest.fixture
    def clean_profile(self):
        """Profile for a clean dataset."""
        return {
            "file_path": "test_clean.csv",
            "basic_stats": {"row_count": 1000, "column_count": 5},
            "missing_values": {},
            "negative_values": {},
            "outliers": {},
            "column_types": {
                "id": {"dtype": "int64", "inferred_type": "numeric"},
                "name": {"dtype": "object", "inferred_type": "categorical"},
            },
            "descriptive_stats": {},
        }

    @pytest.fixture
    def missing_warning_profile(self):
        """Profile with missing values triggering WARNING."""
        return {
            "file_path": "test_missing.csv",
            "basic_stats": {"row_count": 1000, "column_count": 5},
            "missing_values": {
                "age": {"missing_count": 250, "missing_percentage": 25.0}
            },
            "negative_values": {},
            "outliers": {},
            "column_types": {},
            "descriptive_stats": {},
        }

    @pytest.fixture
    def missing_critical_profile(self):
        """Profile with missing values triggering REJECT."""
        return {
            "file_path": "test_critical.csv",
            "basic_stats": {"row_count": 1000, "column_count": 5},
            "missing_values": {
                "user_id": {"missing_count": 500, "missing_percentage": 50.0}
            },
            "negative_values": {},
            "outliers": {},
            "column_types": {},
            "descriptive_stats": {},
        }

    @pytest.fixture
    def empty_profile(self):
        """Profile for an empty dataset."""
        return {
            "file_path": "test_empty.csv",
            "basic_stats": {"row_count": 0, "column_count": 5},
            "missing_values": {},
            "negative_values": {},
            "outliers": {},
            "column_types": {},
            "descriptive_stats": {},
        }

    def test_init(self, rules_loader):
        """Test QualityAgent initialization."""
        agent = QualityAgent(rules_loader)
        assert agent.rules_loader is not None

    def test_analyze_clean_dataset(self, rules_loader, clean_profile):
        """Test analysis of a clean dataset returns ACCEPT."""
        agent = QualityAgent(rules_loader)
        report = agent.analyze(clean_profile)

        assert report.decision == Decision.ACCEPT.value
        assert len(report.issues) == 0

    def test_analyze_missing_warning(self, rules_loader, missing_warning_profile):
        """Test analysis with missing values returns WARNING."""
        agent = QualityAgent(rules_loader)
        report = agent.analyze(missing_warning_profile)

        assert report.decision == Decision.WARNING.value
        assert len(report.issues) >= 1
        assert any("DQ-01" in issue.rule_reference for issue in report.issues)

    def test_analyze_missing_critical(self, rules_loader, missing_critical_profile):
        """Test analysis with critical missing values returns REJECT."""
        agent = QualityAgent(rules_loader)
        report = agent.analyze(missing_critical_profile)

        assert report.decision == Decision.REJECT.value
        assert any(issue.severity == Severity.CRITICAL.value for issue in report.issues)

    def test_analyze_empty_dataset(self, rules_loader, empty_profile):
        """Test analysis of empty dataset returns REJECT."""
        agent = QualityAgent(rules_loader)
        report = agent.analyze(empty_profile)

        assert report.decision == Decision.REJECT.value
        assert any("DQ-02" in issue.rule_reference for issue in report.issues)

    def test_report_structure(self, rules_loader, clean_profile):
        """Test that report has correct structure."""
        agent = QualityAgent(rules_loader)
        report = agent.analyze(clean_profile)

        assert hasattr(report, "decision")
        assert hasattr(report, "summary")
        assert hasattr(report, "issues")
        assert hasattr(report, "stats")
        assert "row_count" in report.stats
        assert "column_count" in report.stats

    def test_report_to_dict(self, rules_loader, clean_profile):
        """Test report serialization to dict."""
        agent = QualityAgent(rules_loader)
        report = agent.analyze(clean_profile)
        report_dict = report.to_dict()

        assert isinstance(report_dict, dict)
        assert "decision" in report_dict
        assert "summary" in report_dict
        assert "issues" in report_dict


class TestDecisionEnum:
    """Tests for Decision enum."""

    def test_decision_values(self):
        """Test Decision enum has correct values."""
        assert Decision.ACCEPT.value == "ACCEPT"
        assert Decision.WARNING.value == "WARNING"
        assert Decision.REJECT.value == "REJECT"


class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test Severity enum has correct values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"


class TestIssue:
    """Tests for Issue dataclass."""

    def test_issue_creation(self):
        """Test creating an Issue."""
        issue = Issue(
            type="Missing values",
            severity=Severity.HIGH.value,
            rule_reference="DQ-01",
            explanation="Column 'age' has 25% missing values",
            column="age"
        )
        assert issue.type == "Missing values"
        assert issue.column == "age"

    def test_issue_without_column(self):
        """Test creating an Issue without column."""
        issue = Issue(
            type="Empty dataset",
            severity=Severity.CRITICAL.value,
            rule_reference="DQ-02",
            explanation="Dataset has 0 rows"
        )
        assert issue.column is None
