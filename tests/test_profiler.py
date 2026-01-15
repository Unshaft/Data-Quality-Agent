"""
Unit tests for the DataProfiler module.
"""

import pytest
import pandas as pd
from pathlib import Path

from profiling.profiler import DataProfiler


class TestDataProfiler:
    """Tests for DataProfiler class."""

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file for testing."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", None, "Eve"],
            "age": [25, 30, None, 40, 35],
            "salary": [50000, 60000, 55000, 70000, -5000],
            "department": ["IT", "HR", "IT", "Finance", "HR"],
        })
        csv_path = tmp_path / "test_data.csv"
        df.to_csv(csv_path, index=False)
        return str(csv_path)

    @pytest.fixture
    def empty_csv(self, tmp_path):
        """Create an empty CSV file for testing."""
        df = pd.DataFrame(columns=["id", "name", "age"])
        csv_path = tmp_path / "empty_data.csv"
        df.to_csv(csv_path, index=False)
        return str(csv_path)

    def test_init(self, sample_csv):
        """Test DataProfiler initialization."""
        profiler = DataProfiler(sample_csv)
        assert profiler.filepath == Path(sample_csv)

    def test_load_data(self, sample_csv):
        """Test data loading."""
        profiler = DataProfiler(sample_csv)
        df = profiler.load_data()
        assert len(df) == 5
        assert len(df.columns) == 5

    def test_profile_basic_stats(self, sample_csv):
        """Test that generate_profile returns correct basic stats."""
        profiler = DataProfiler(sample_csv)
        profile = profiler.generate_profile()

        assert profile["basic_stats"]["row_count"] == 5
        assert profile["basic_stats"]["column_count"] == 5

    def test_profile_missing_values(self, sample_csv):
        """Test missing values detection."""
        profiler = DataProfiler(sample_csv)
        profile = profiler.generate_profile()

        missing = profile["missing_values"]
        # 'name' has 1 missing out of 5 = 20%
        assert "name" in missing
        assert missing["name"]["missing_percentage"] == 20.0
        # 'age' has 1 missing out of 5 = 20%
        assert "age" in missing
        assert missing["age"]["missing_percentage"] == 20.0

    def test_profile_negative_values(self, sample_csv):
        """Test negative values detection."""
        profiler = DataProfiler(sample_csv)
        profile = profiler.generate_profile()

        negative = profile["negative_values"]
        # 'salary' has 1 negative value (-5000)
        assert "salary" in negative
        assert negative["salary"]["negative_count"] == 1

    def test_profile_column_types(self, sample_csv):
        """Test column types detection."""
        profiler = DataProfiler(sample_csv)
        profile = profiler.generate_profile()

        types = profile["column_types"]
        assert "id" in types
        assert "name" in types
        # department is a string column
        assert "semantic_type" in types["department"]

    def test_empty_dataset(self, empty_csv):
        """Test profiling an empty dataset."""
        profiler = DataProfiler(empty_csv)
        profile = profiler.generate_profile()

        assert profile["basic_stats"]["row_count"] == 0
        assert profile["basic_stats"]["column_count"] == 3

    def test_file_not_found(self):
        """Test error handling for non-existent file."""
        profiler = DataProfiler("nonexistent.csv")
        with pytest.raises(FileNotFoundError):
            profiler.generate_profile()

    def test_descriptive_stats(self, sample_csv):
        """Test descriptive statistics for numeric columns."""
        profiler = DataProfiler(sample_csv)
        profile = profiler.generate_profile()

        stats = profile["descriptive_stats"]
        assert "age" in stats
        assert "min" in stats["age"]
        assert "max" in stats["age"]
        assert "mean" in stats["age"]

    def test_get_basic_stats_without_load(self, sample_csv):
        """Test that methods work even without explicit load_data call."""
        profiler = DataProfiler(sample_csv)
        # generate_profile should handle loading internally
        profile = profiler.generate_profile()
        assert profile["basic_stats"]["row_count"] == 5
