"""
Unit tests for the RulesLoader module.
"""

import pytest
from pathlib import Path

from rag.rules_loader import RulesLoader


class TestRulesLoader:
    """Tests for RulesLoader class."""

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

## DQ-03 - Type mismatch
**Severity**: WARNING
**Description**: Column contains mixed data types.
"""
        rules_file = tmp_path / "test_rules.md"
        rules_file.write_text(rules_content, encoding="utf-8")
        return str(tmp_path)

    def test_init(self, rules_dir):
        """Test RulesLoader initialization."""
        loader = RulesLoader(rules_dir)
        assert loader.rules_dir == Path(rules_dir)

    def test_load_rules(self, rules_dir):
        """Test loading rules from markdown files."""
        loader = RulesLoader(rules_dir)
        rules = loader.load_rules()

        assert len(rules) == 3
        rule_ids = [r.id for r in rules]
        assert "DQ-01" in rule_ids
        assert "DQ-02" in rule_ids
        assert "DQ-03" in rule_ids

    def test_rule_structure(self, rules_dir):
        """Test that loaded rules have correct structure."""
        loader = RulesLoader(rules_dir)
        rules = loader.load_rules()

        dq01 = next(r for r in rules if r.id == "DQ-01")
        assert dq01.title == "Missing values"
        assert "Detect columns with missing values" in dq01.content

    def test_get_rule_by_id(self, rules_dir):
        """Test retrieving a specific rule by ID."""
        loader = RulesLoader(rules_dir)
        loader.load_rules()

        rule = loader.get_rule_by_id("DQ-02")
        assert rule is not None
        assert rule.id == "DQ-02"
        assert "Empty dataset" in rule.title

    def test_get_nonexistent_rule(self, rules_dir):
        """Test retrieving a non-existent rule."""
        loader = RulesLoader(rules_dir)
        loader.load_rules()

        rule = loader.get_rule_by_id("DQ-99")
        assert rule is None

    def test_empty_directory(self, tmp_path):
        """Test loading from directory with no markdown files."""
        loader = RulesLoader(str(tmp_path))
        rules = loader.load_rules()
        assert rules == []

    def test_search_rules(self, rules_dir):
        """Test searching rules by keyword."""
        loader = RulesLoader(rules_dir)
        loader.load_rules()

        results = loader.search_rules("missing")
        assert len(results) >= 1
        assert any(r.id == "DQ-01" for r in results)

    def test_get_rules_summary(self, rules_dir):
        """Test getting rules summary."""
        loader = RulesLoader(rules_dir)
        loader.load_rules()

        summary = loader.get_rules_summary()
        assert len(summary) == 3
        assert all("id" in s and "title" in s for s in summary)

    def test_get_all_rules_text(self, rules_dir):
        """Test getting all rules as text."""
        loader = RulesLoader(rules_dir)
        loader.load_rules()

        text = loader.get_all_rules_text()
        assert "DQ-01" in text
        assert "DQ-02" in text
        assert "DQ-03" in text
