"""
Pytest configuration and shared fixtures.
"""

import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary directory with test data files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def create_test_csv(test_data_dir):
    """Factory fixture to create test CSV files."""
    def _create_csv(name: str, df: pd.DataFrame) -> str:
        path = test_data_dir / name
        df.to_csv(path, index=False)
        return str(path)
    return _create_csv


@pytest.fixture
def clean_dataframe():
    """A clean DataFrame with no quality issues."""
    return pd.DataFrame({
        "id": range(1, 101),
        "name": [f"User_{i}" for i in range(1, 101)],
        "age": [25 + (i % 40) for i in range(100)],
        "salary": [50000 + (i * 100) for i in range(100)],
    })


@pytest.fixture
def missing_dataframe():
    """A DataFrame with missing values."""
    df = pd.DataFrame({
        "id": range(1, 101),
        "name": [f"User_{i}" if i % 4 != 0 else None for i in range(1, 101)],
        "age": [25 + (i % 40) if i % 3 != 0 else None for i in range(100)],
        "salary": [50000 + (i * 100) for i in range(100)],
    })
    return df


@pytest.fixture
def outliers_dataframe():
    """A DataFrame with outliers."""
    ages = [30] * 90 + [200, 250, 300, -50, -100, 500, 1000, 2000, 3000, 5000]
    return pd.DataFrame({
        "id": range(1, 101),
        "name": [f"User_{i}" for i in range(1, 101)],
        "age": ages,
        "salary": [50000] * 100,
    })
