"""
LangChain tools for the Quality Agent.
These tools provide the agent with capabilities to analyze data and consult rules.
"""

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# Runtime context - injected before agent execution
_profile_data: dict[str, Any] = {}
_vector_store = None


def set_context(profile: dict[str, Any], vector_store) -> None:
    """
    Set the runtime context for tools.

    Args:
        profile: Data profile from DataProfiler.
        vector_store: VectorRulesStore instance.
    """
    global _profile_data, _vector_store
    _profile_data = profile
    _vector_store = vector_store
    logger.debug("Tool context set with profile and vector store")


@tool
def get_dataset_overview() -> str:
    """
    Get a high-level overview of the dataset.
    Returns row count, column count, and column type distribution.
    Use this first to understand the dataset structure.
    """
    basic = _profile_data.get("basic_stats", {})
    types = _profile_data.get("column_types", {})

    result = f"Dataset Overview:\n"
    result += f"- File: {_profile_data.get('file_path', 'N/A')}\n"
    result += f"- Total rows: {basic.get('row_count', 'N/A'):,}\n"
    result += f"- Total columns: {basic.get('column_count', 'N/A')}\n\n"

    # Check for empty dataset
    if basic.get("row_count", 0) == 0:
        result += "WARNING: Dataset is EMPTY (0 rows)!\n"
        return result

    # Summarize column types
    type_counts: dict[str, int] = {}
    for col, info in types.items():
        sem_type = info.get("semantic_type", "unknown")
        type_counts[sem_type] = type_counts.get(sem_type, 0) + 1

    result += "Column types:\n"
    for t, count in sorted(type_counts.items()):
        result += f"  - {t}: {count} columns\n"

    return result


@tool
def get_missing_values_stats() -> str:
    """
    Get statistics about missing values in the dataset.
    Returns columns with missing values and their percentages.
    Use this to check for DQ-01 (Missing values) rule violations.
    """
    missing = _profile_data.get("missing_values", {})
    if not missing:
        return "No missing values data available."

    # Filter to columns with missing values
    with_missing = {
        k: v for k, v in missing.items()
        if v["missing_percentage"] > 0
    }

    if not with_missing:
        return "No columns have missing values. All data is complete."

    # Sort by percentage descending
    sorted_missing = sorted(
        with_missing.items(),
        key=lambda x: -x[1]["missing_percentage"]
    )

    result = f"Missing values analysis ({len(with_missing)} columns affected):\n\n"

    # Categorize by severity
    critical = [(k, v) for k, v in sorted_missing if v["missing_percentage"] >= 40]
    warning = [(k, v) for k, v in sorted_missing if 20 <= v["missing_percentage"] < 40]
    minor = [(k, v) for k, v in sorted_missing if v["missing_percentage"] < 20]

    if critical:
        result += "CRITICAL (>= 40% missing - may trigger REJECT):\n"
        for col, stats in critical:
            result += f"  - {col}: {stats['missing_percentage']:.1f}% ({stats['missing_count']:,} values)\n"
        result += "\n"

    if warning:
        result += "WARNING (20-40% missing):\n"
        for col, stats in warning:
            result += f"  - {col}: {stats['missing_percentage']:.1f}% ({stats['missing_count']:,} values)\n"
        result += "\n"

    if minor:
        result += f"Minor (< 20% missing): {len(minor)} columns\n"
        for col, stats in minor[:5]:  # Show top 5
            result += f"  - {col}: {stats['missing_percentage']:.1f}%\n"
        if len(minor) > 5:
            result += f"  ... and {len(minor) - 5} more\n"

    return result


@tool
def get_outlier_stats() -> str:
    """
    Get statistics about outliers in numeric columns using IQR method.
    Returns columns with outliers exceeding 5% threshold.
    Use this to check for DQ-05 (Outliers) rule violations.
    """
    outliers = _profile_data.get("outliers", {})
    if not outliers:
        return "No outlier data available."

    # Filter to columns with significant outliers (> 1%)
    with_outliers = {
        k: v for k, v in outliers.items()
        if v["outlier_percentage"] > 1
    }

    if not with_outliers:
        return "No significant outliers detected (all columns < 1% outliers)."

    # Sort by percentage descending
    sorted_outliers = sorted(
        with_outliers.items(),
        key=lambda x: -x[1]["outlier_percentage"]
    )

    result = f"Outlier analysis (IQR method) - {len(with_outliers)} columns with outliers:\n\n"

    # Categorize
    warning = [(k, v) for k, v in sorted_outliers if v["outlier_percentage"] >= 5]
    minor = [(k, v) for k, v in sorted_outliers if v["outlier_percentage"] < 5]

    if warning:
        result += "WARNING (>= 5% outliers - exceeds threshold):\n"
        for col, stats in warning:
            result += f"  - {col}: {stats['outlier_percentage']:.1f}% outliers\n"
            result += f"    Valid range: [{stats['lower_bound']:.2f}, {stats['upper_bound']:.2f}]\n"
        result += "\n"

    if minor:
        result += f"Minor (1-5% outliers): {len(minor)} columns\n"
        for col, stats in minor[:3]:
            result += f"  - {col}: {stats['outlier_percentage']:.1f}%\n"

    return result


@tool
def get_negative_values_stats() -> str:
    """
    Get statistics about negative values in numeric columns.
    Returns columns with negative values that may be invalid.
    Use this to check for DQ-04 (Negative values) rule violations.
    """
    negatives = _profile_data.get("negative_values", {})
    if not negatives:
        return "No negative values detected in any column."

    result = f"Negative values detected in {len(negatives)} columns:\n\n"

    # Known columns where negatives are impossible
    impossible_negative = {
        "age", "weekly_purchases", "monthly_spend", "average_order_value",
        "household_size", "referral_count", "impulse_purchases_per_month",
        "hobby_count", "daily_session_time_minutes", "product_views_per_day",
        "ad_views_per_day", "ad_clicks_per_day", "wishlist_items_count",
        "cart_items_average", "checkout_abandonments_per_month", "account_age_months"
    }

    violations = []
    other = []

    for col, stats in negatives.items():
        if col in impossible_negative:
            violations.append((col, stats))
        else:
            other.append((col, stats))

    if violations:
        result += "INVALID NEGATIVES (should not be negative):\n"
        for col, stats in violations:
            result += f"  - {col}: {stats['negative_count']} negative values ({stats['negative_percentage']:.1f}%)\n"
        result += "\n"

    if other:
        result += "Other columns with negatives (may be valid):\n"
        for col, stats in other:
            result += f"  - {col}: {stats['negative_count']} values ({stats['negative_percentage']:.1f}%)\n"

    return result


@tool
def get_descriptive_stats(column_name: str) -> str:
    """
    Get descriptive statistics for a specific numeric column.
    Includes min, max, mean, median, and standard deviation.

    Args:
        column_name: Name of the column to get stats for.
    """
    stats = _profile_data.get("descriptive_stats", {})

    if column_name not in stats:
        available = list(stats.keys())[:10]
        return f"No statistics for '{column_name}'. Available: {available}"

    col_stats = stats[column_name]
    result = f"Statistics for '{column_name}':\n"
    result += f"  - Min: {col_stats['min']}\n"
    result += f"  - Max: {col_stats['max']}\n"
    result += f"  - Mean: {col_stats['mean']:.2f}\n"
    result += f"  - Median: {col_stats['median']}\n"
    result += f"  - Std Dev: {col_stats['std']:.2f}\n"

    # Check for outliers in this column
    outliers = _profile_data.get("outliers", {}).get(column_name, {})
    if outliers:
        result += f"\n  Outliers: {outliers.get('outlier_percentage', 0):.1f}%\n"
        result += f"  Valid range: [{outliers.get('lower_bound', 'N/A')}, {outliers.get('upper_bound', 'N/A')}]\n"

    return result


@tool
def search_quality_rules(issue_description: str) -> str:
    """
    Search for relevant quality rules based on an issue description.
    Uses semantic search to find the most applicable rules.

    Args:
        issue_description: Description of the data quality issue (e.g., "missing values in age column").
    """
    if _vector_store is None:
        return "Vector store not initialized. Cannot search rules."

    results = _vector_store.search_relevant_rules(issue_description, n_results=3)

    if not results:
        return "No relevant rules found for this issue."

    output = f"Relevant rules for '{issue_description}':\n\n"

    for i, rule in enumerate(results, 1):
        output += f"[{i}] {rule['metadata']['rule_id']}: {rule['metadata']['title']}\n"
        output += "-" * 40 + "\n"
        # Truncate long documents
        doc = rule['document']
        if len(doc) > 500:
            doc = doc[:500] + "..."
        output += doc + "\n\n"

    return output


def get_all_tools() -> list:
    """
    Return all available tools for the agent.

    Returns:
        List of LangChain tool functions.
    """
    return [
        get_dataset_overview,
        get_missing_values_stats,
        get_outlier_stats,
        get_negative_values_stats,
        get_descriptive_stats,
        search_quality_rules,
    ]
