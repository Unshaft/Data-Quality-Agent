"""
Data Profiler module.
Extracts factual quality metrics from tabular datasets.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataProfiler:
    """
    Extracts factual data quality metrics from a dataset.

    This class is responsible for producing measurable facts about the data,
    without making any judgments or decisions. It serves as the "facts" layer
    in the architecture.
    """

    def __init__(self, filepath: str | Path):
        """
        Initialize the profiler with a dataset path.

        Args:
            filepath: Path to the CSV file to profile.
        """
        self.filepath = Path(filepath)
        self.df: pd.DataFrame | None = None
        logger.info(f"DataProfiler initialized with file: {self.filepath}")

    def load_data(self) -> pd.DataFrame:
        """
        Load the CSV dataset into memory.

        Returns:
            The loaded DataFrame.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            pd.errors.EmptyDataError: If the file is empty.
        """
        logger.info(f"Loading dataset from {self.filepath}")

        if not self.filepath.exists():
            logger.error(f"File not found: {self.filepath}")
            raise FileNotFoundError(f"Dataset not found: {self.filepath}")

        self.df = pd.read_csv(self.filepath)
        logger.info(f"Dataset loaded: {len(self.df)} rows, {len(self.df.columns)} columns")

        return self.df

    def get_basic_stats(self) -> dict[str, Any]:
        """
        Extract basic dataset statistics.

        Returns:
            Dictionary containing row count, column count, and column names.
        """
        if self.df is None:
            self.load_data()

        stats = {
            "row_count": len(self.df),
            "column_count": len(self.df.columns),
            "columns": list(self.df.columns),
        }

        logger.debug(f"Basic stats: {stats['row_count']} rows, {stats['column_count']} columns")
        return stats

    def get_column_types(self) -> dict[str, dict[str, str]]:
        """
        Analyze column data types.

        Returns:
            Dictionary mapping column names to their detected types.
        """
        if self.df is None:
            self.load_data()

        types = {}
        for col in self.df.columns:
            pandas_dtype = str(self.df[col].dtype)

            # Infer semantic type
            if pd.api.types.is_integer_dtype(self.df[col]):
                semantic_type = "integer"
            elif pd.api.types.is_float_dtype(self.df[col]):
                semantic_type = "numeric"
            elif pd.api.types.is_bool_dtype(self.df[col]):
                semantic_type = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(self.df[col]):
                semantic_type = "datetime"
            else:
                # Check if it looks like a date string
                if col.endswith("_date") or "date" in col.lower():
                    semantic_type = "date_string"
                else:
                    semantic_type = "string"

            types[col] = {
                "pandas_dtype": pandas_dtype,
                "semantic_type": semantic_type,
            }

        logger.debug(f"Analyzed types for {len(types)} columns")
        return types

    def get_missing_values(self) -> dict[str, dict[str, Any]]:
        """
        Analyze missing values per column.

        Returns:
            Dictionary with missing value counts and percentages per column.
        """
        if self.df is None:
            self.load_data()

        total_rows = len(self.df)
        missing = {}

        for col in self.df.columns:
            null_count = self.df[col].isnull().sum()
            missing[col] = {
                "missing_count": int(null_count),
                "missing_percentage": round(null_count / total_rows * 100, 2) if total_rows > 0 else 0.0,
            }

        # Log columns with significant missing values
        significant_missing = {k: v for k, v in missing.items() if v["missing_percentage"] > 5}
        if significant_missing:
            logger.info(f"Columns with >5% missing values: {list(significant_missing.keys())}")

        return missing

    def get_descriptive_stats(self) -> dict[str, dict[str, Any]]:
        """
        Compute descriptive statistics for numeric columns.

        Returns:
            Dictionary with min, max, mean, median, std for numeric columns.
        """
        if self.df is None:
            self.load_data()

        stats = {}
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            col_data = self.df[col].dropna()
            if len(col_data) > 0:
                stats[col] = {
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "mean": round(float(col_data.mean()), 2),
                    "median": float(col_data.median()),
                    "std": round(float(col_data.std()), 2),
                }

        logger.debug(f"Computed descriptive stats for {len(stats)} numeric columns")
        return stats

    def detect_outliers_iqr(self) -> dict[str, dict[str, Any]]:
        """
        Detect outliers using the IQR (Interquartile Range) method.

        An outlier is defined as a value below Q1 - 1.5*IQR or above Q3 + 1.5*IQR.

        Returns:
            Dictionary with outlier counts and percentages per numeric column.
        """
        if self.df is None:
            self.load_data()

        outliers = {}
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        total_rows = len(self.df)

        for col in numeric_cols:
            col_data = self.df[col].dropna()
            if len(col_data) == 0:
                continue

            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (col_data < lower_bound) | (col_data > upper_bound)
            outlier_count = outlier_mask.sum()

            outliers[col] = {
                "outlier_count": int(outlier_count),
                "outlier_percentage": round(outlier_count / total_rows * 100, 2) if total_rows > 0 else 0.0,
                "lower_bound": round(float(lower_bound), 2),
                "upper_bound": round(float(upper_bound), 2),
                "q1": round(float(q1), 2),
                "q3": round(float(q3), 2),
            }

        # Log columns with significant outliers
        significant_outliers = {k: v for k, v in outliers.items() if v["outlier_percentage"] > 5}
        if significant_outliers:
            logger.info(f"Columns with >5% outliers: {list(significant_outliers.keys())}")

        return outliers

    def detect_negative_values(self) -> dict[str, dict[str, Any]]:
        """
        Detect negative values in numeric columns.

        Returns:
            Dictionary with negative value counts and percentages per numeric column.
        """
        if self.df is None:
            self.load_data()

        negatives = {}
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        total_rows = len(self.df)

        for col in numeric_cols:
            col_data = self.df[col].dropna()
            negative_count = (col_data < 0).sum()

            if negative_count > 0:
                negatives[col] = {
                    "negative_count": int(negative_count),
                    "negative_percentage": round(negative_count / total_rows * 100, 2) if total_rows > 0 else 0.0,
                }

        if negatives:
            logger.info(f"Columns with negative values: {list(negatives.keys())}")

        return negatives

    def generate_profile(self) -> dict[str, Any]:
        """
        Generate a complete data quality profile.

        This is the main entry point that aggregates all profiling metrics
        into a single structured report.

        Returns:
            Complete profile dictionary with all metrics.
        """
        logger.info("=" * 60)
        logger.info("Starting data profiling...")
        logger.info("=" * 60)

        # Ensure data is loaded
        if self.df is None:
            self.load_data()

        profile = {
            "file_path": str(self.filepath),
            "basic_stats": self.get_basic_stats(),
            "column_types": self.get_column_types(),
            "missing_values": self.get_missing_values(),
            "descriptive_stats": self.get_descriptive_stats(),
            "outliers": self.detect_outliers_iqr(),
            "negative_values": self.detect_negative_values(),
        }

        logger.info("=" * 60)
        logger.info("Data profiling completed successfully")
        logger.info("=" * 60)

        return profile
