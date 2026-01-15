"""
Quality Agent module.
Applies reasoning over data profile and rules to produce decisions.
"""

import logging
from typing import Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from rag.rules_loader import RulesLoader

logger = logging.getLogger(__name__)


class Decision(str, Enum):
    """Possible quality decisions."""

    ACCEPT = "ACCEPT"
    WARNING = "WARNING"
    REJECT = "REJECT"


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Issue:
    """
    Represents a detected data quality issue.

    Attributes:
        type: Category of the issue
        severity: Severity level
        rule_reference: Associated rule ID
        explanation: Detailed explanation
        column: Affected column (if applicable)
    """

    type: str
    severity: str
    rule_reference: str
    explanation: str
    column: str | None = None


@dataclass
class QualityReport:
    """
    Final quality assessment report.

    Attributes:
        decision: Global decision (ACCEPT, WARNING, REJECT)
        summary: Human-readable summary
        issues: List of detected issues
        stats: Basic dataset statistics
    """

    decision: str
    summary: str
    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "decision": self.decision,
            "summary": self.summary,
            "issues": [asdict(issue) for issue in self.issues],
            "stats": self.stats,
        }


class QualityAgent:
    """
    AI Agent that reasons about data quality.

    This agent receives a data profile, consults quality rules,
    applies explicit reasoning, and produces a justified decision.
    """

    # Thresholds for decision making
    MISSING_WARNING_THRESHOLD = 20.0  # % missing triggers warning
    MISSING_REJECT_THRESHOLD = 40.0  # % missing triggers reject
    OUTLIER_WARNING_THRESHOLD = 5.0  # % outliers triggers warning

    # Critical columns that require stricter checks
    CRITICAL_COLUMNS = {
        "user_id",
        "age",
        "gender",
        "country",
        "income_level",
        "weekly_purchases",
        "monthly_spend",
        "average_order_value",
        "last_purchase_date",
    }

    # Columns where negative values are impossible
    NO_NEGATIVE_COLUMNS = {
        "age",
        "weekly_purchases",
        "monthly_spend",
        "average_order_value",
        "household_size",
        "referral_count",
        "impulse_purchases_per_month",
        "hobby_count",
        "daily_session_time_minutes",
        "product_views_per_day",
        "ad_views_per_day",
        "ad_clicks_per_day",
        "wishlist_items_count",
        "cart_items_average",
        "checkout_abandonments_per_month",
        "account_age_months",
    }

    def __init__(self, rules_loader: RulesLoader):
        """
        Initialize the quality agent.

        Args:
            rules_loader: Loaded RulesLoader instance with quality rules.
        """
        self.rules_loader = rules_loader
        self.issues: list[Issue] = []
        self.reasoning_log: list[str] = []
        logger.info("QualityAgent initialized")

    def _log_reasoning(self, message: str) -> None:
        """
        Log a reasoning step.

        Args:
            message: The reasoning step to log.
        """
        self.reasoning_log.append(message)
        logger.info(f"[REASONING] {message}")

    def _check_empty_dataset(self, profile: dict[str, Any]) -> bool:
        """
        Check if the dataset is empty (DQ-02).

        Args:
            profile: The data profile.

        Returns:
            True if dataset is empty (triggers REJECT).
        """
        self._log_reasoning("Step 1: Checking if dataset is empty (DQ-02)")

        row_count = profile["basic_stats"]["row_count"]

        if row_count == 0:
            self._log_reasoning("  -> Dataset is EMPTY. This triggers REJECT.")
            self.issues.append(
                Issue(
                    type="Empty dataset",
                    severity=Severity.CRITICAL.value,
                    rule_reference="DQ-02",
                    explanation="Dataset contains 0 rows. Cannot perform quality analysis on empty data.",
                )
            )
            return True

        self._log_reasoning(f"  -> Dataset has {row_count} rows. Proceeding with analysis.")
        return False

    def _check_missing_values(self, profile: dict[str, Any]) -> None:
        """
        Analyze missing values (DQ-01).

        Args:
            profile: The data profile.
        """
        self._log_reasoning("Step 2: Analyzing missing values (DQ-01)")

        missing_values = profile["missing_values"]

        for col, stats in missing_values.items():
            pct = stats["missing_percentage"]

            if pct >= self.MISSING_REJECT_THRESHOLD:
                severity = Severity.CRITICAL.value if col in self.CRITICAL_COLUMNS else Severity.HIGH.value
                self._log_reasoning(f"  -> Column '{col}': {pct}% missing (>= {self.MISSING_REJECT_THRESHOLD}%) - {severity.upper()}")
                self.issues.append(
                    Issue(
                        type="Missing values",
                        severity=severity,
                        rule_reference="DQ-01",
                        explanation=f"Column '{col}' has {pct}% missing values, exceeding the {self.MISSING_REJECT_THRESHOLD}% threshold.",
                        column=col,
                    )
                )
            elif pct >= self.MISSING_WARNING_THRESHOLD:
                severity = Severity.MEDIUM.value if col in self.CRITICAL_COLUMNS else Severity.LOW.value
                self._log_reasoning(f"  -> Column '{col}': {pct}% missing (>= {self.MISSING_WARNING_THRESHOLD}%) - {severity.upper()}")
                self.issues.append(
                    Issue(
                        type="Missing values",
                        severity=severity,
                        rule_reference="DQ-01",
                        explanation=f"Column '{col}' has {pct}% missing values, exceeding the {self.MISSING_WARNING_THRESHOLD}% threshold.",
                        column=col,
                    )
                )

        if not any(issue.rule_reference == "DQ-01" for issue in self.issues):
            self._log_reasoning("  -> No significant missing value issues detected.")

    def _check_outliers(self, profile: dict[str, Any]) -> None:
        """
        Analyze outliers using IQR method (DQ-05).

        Args:
            profile: The data profile.
        """
        self._log_reasoning("Step 3: Analyzing outliers with IQR method (DQ-05)")

        outliers = profile.get("outliers", {})

        for col, stats in outliers.items():
            pct = stats["outlier_percentage"]

            if pct >= self.OUTLIER_WARNING_THRESHOLD:
                self._log_reasoning(f"  -> Column '{col}': {pct}% outliers (>= {self.OUTLIER_WARNING_THRESHOLD}%) - WARNING")
                self.issues.append(
                    Issue(
                        type="Outliers",
                        severity=Severity.MEDIUM.value,
                        rule_reference="DQ-05",
                        explanation=f"Column '{col}' has {pct}% outliers (values outside [{stats['lower_bound']}, {stats['upper_bound']}]).",
                        column=col,
                    )
                )

        if not any(issue.rule_reference == "DQ-05" for issue in self.issues):
            self._log_reasoning("  -> No significant outlier issues detected.")

    def _check_negative_values(self, profile: dict[str, Any]) -> None:
        """
        Check for impossible negative values (DQ-04).

        Args:
            profile: The data profile.
        """
        self._log_reasoning("Step 4: Checking for impossible negative values (DQ-04)")

        negative_values = profile.get("negative_values", {})

        for col, stats in negative_values.items():
            if col in self.NO_NEGATIVE_COLUMNS:
                self._log_reasoning(f"  -> Column '{col}': {stats['negative_count']} negative values found - WARNING")
                self.issues.append(
                    Issue(
                        type="Negative values",
                        severity=Severity.MEDIUM.value,
                        rule_reference="DQ-04",
                        explanation=f"Column '{col}' contains {stats['negative_count']} negative values ({stats['negative_percentage']}%), which should not be possible for this field.",
                        column=col,
                    )
                )

        if not any(issue.rule_reference == "DQ-04" for issue in self.issues):
            self._log_reasoning("  -> No impossible negative values detected.")

    def _determine_decision(self) -> Decision:
        """
        Determine the global decision based on detected issues.

        Returns:
            The final Decision (ACCEPT, WARNING, or REJECT).
        """
        self._log_reasoning("Step 5: Determining global decision")

        if not self.issues:
            self._log_reasoning("  -> No issues detected. Decision: ACCEPT")
            return Decision.ACCEPT

        # Check for critical issues
        critical_issues = [i for i in self.issues if i.severity == Severity.CRITICAL.value]
        high_issues = [i for i in self.issues if i.severity == Severity.HIGH.value]

        if critical_issues:
            self._log_reasoning(f"  -> Found {len(critical_issues)} CRITICAL issue(s). Decision: REJECT")
            return Decision.REJECT

        if high_issues:
            self._log_reasoning(f"  -> Found {len(high_issues)} HIGH severity issue(s). Decision: REJECT")
            return Decision.REJECT

        self._log_reasoning(f"  -> Found {len(self.issues)} issue(s), none critical. Decision: WARNING")
        return Decision.WARNING

    def _generate_summary(self, decision: Decision, profile: dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the analysis.

        Args:
            decision: The determined decision.
            profile: The data profile.

        Returns:
            Summary string.
        """
        row_count = profile["basic_stats"]["row_count"]
        col_count = profile["basic_stats"]["column_count"]

        if decision == Decision.ACCEPT:
            return f"Dataset with {row_count:,} rows and {col_count} columns passed all quality checks."

        if decision == Decision.WARNING:
            issue_count = len(self.issues)
            return f"Dataset with {row_count:,} rows and {col_count} columns has {issue_count} quality issue(s) requiring attention."

        # REJECT
        critical_count = len([i for i in self.issues if i.severity in [Severity.CRITICAL.value, Severity.HIGH.value]])
        return f"Dataset with {row_count:,} rows and {col_count} columns has {critical_count} critical quality issue(s). Manual review required."

    def analyze(self, profile: dict[str, Any]) -> QualityReport:
        """
        Perform complete quality analysis on a data profile.

        This is the main entry point for the agent's reasoning process.
        It applies step-by-step reasoning, consults rules, and produces
        a justified decision.

        Args:
            profile: The data profile from DataProfiler.

        Returns:
            QualityReport with decision, summary, and issues.
        """
        logger.info("=" * 60)
        logger.info("Starting quality analysis...")
        logger.info("=" * 60)

        # Reset state for new analysis
        self.issues = []
        self.reasoning_log = []

        # Step-by-step reasoning
        self._log_reasoning("Beginning data quality analysis")
        self._log_reasoning(f"Consulting {len(self.rules_loader.rules)} quality rules")

        # Check for empty dataset first (immediate reject)
        if self._check_empty_dataset(profile):
            decision = Decision.REJECT
        else:
            # Run all quality checks
            self._check_missing_values(profile)
            self._check_outliers(profile)
            self._check_negative_values(profile)

            # Determine final decision
            decision = self._determine_decision()

        # Generate summary
        summary = self._generate_summary(decision, profile)

        # Create report
        report = QualityReport(
            decision=decision.value,
            summary=summary,
            issues=self.issues,
            stats={
                "row_count": profile["basic_stats"]["row_count"],
                "column_count": profile["basic_stats"]["column_count"],
                "issues_count": len(self.issues),
            },
        )

        logger.info("=" * 60)
        logger.info(f"Quality analysis completed. Decision: {decision.value}")
        logger.info("=" * 60)

        return report
