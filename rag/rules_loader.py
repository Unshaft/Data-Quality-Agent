"""
Rules Loader module.
Loads and provides access to data quality rules from markdown/text files.
"""

import logging
import re
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """
    Represents a single data quality rule.

    Attributes:
        id: Unique identifier (e.g., "DQ-01")
        title: Short title of the rule
        content: Full text content of the rule
        severity_warning: Conditions that trigger a WARNING
        severity_reject: Conditions that trigger a REJECT
    """

    id: str
    title: str
    content: str
    severity_warning: str | None = None
    severity_reject: str | None = None


class RulesLoader:
    """
    Loads and manages data quality rules from markdown files.

    This class serves as the "knowledge" layer in the architecture,
    providing structured access to documented quality rules.
    """

    def __init__(self, rules_dir: str | Path):
        """
        Initialize the rules loader.

        Args:
            rules_dir: Path to the directory containing rule files.
        """
        self.rules_dir = Path(rules_dir)
        self.rules: list[Rule] = []
        self.rules_text: str = ""
        logger.info(f"RulesLoader initialized with directory: {self.rules_dir}")

    def load_rules(self) -> list[Rule]:
        """
        Load all rules from markdown files in the rules directory.

        Returns:
            List of parsed Rule objects.
        """
        logger.info(f"Loading rules from {self.rules_dir}")

        if not self.rules_dir.exists():
            logger.error(f"Rules directory not found: {self.rules_dir}")
            raise FileNotFoundError(f"Rules directory not found: {self.rules_dir}")

        # Load all .md and .txt files
        rule_files = list(self.rules_dir.glob("*.md")) + list(self.rules_dir.glob("*.txt"))

        if not rule_files:
            logger.warning("No rule files found in directory")
            return []

        all_text = []
        for file_path in rule_files:
            logger.info(f"Loading rules from: {file_path.name}")
            content = file_path.read_text(encoding="utf-8")
            all_text.append(content)
            self._parse_rules_from_content(content)

        self.rules_text = "\n\n".join(all_text)
        logger.info(f"Loaded {len(self.rules)} rules from {len(rule_files)} file(s)")

        return self.rules

    def _parse_rules_from_content(self, content: str) -> None:
        """
        Parse rules from markdown content.

        Extracts rules following the pattern:
        ## DQ-XX – Title
        Content...

        Args:
            content: Raw markdown content.
        """
        # Normalize various dash characters to standard hyphen for parsing
        # Handles: en-dash (–), em-dash (—), non-breaking hyphen (‑), minus (−)
        normalized_content = content
        for dash_char in ["–", "—", "‑", "−"]:
            normalized_content = normalized_content.replace(dash_char, "-")

        # Pattern to match rule headers like "## DQ-01 - Title"
        rule_pattern = r"##\s+(DQ-\d+)\s*-\s*(.+?)(?=\n)"
        matches = list(re.finditer(rule_pattern, normalized_content))

        for i, match in enumerate(matches):
            rule_id = match.group(1)
            title = match.group(2).strip()

            # Get content until next rule or end
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized_content)
            rule_content = normalized_content[start:end].strip()

            # Extract severity conditions if present
            severity_warning = None
            severity_reject = None

            warning_match = re.search(r"WARNING[:\s]+(.+?)(?=REJECT|$)", rule_content, re.IGNORECASE | re.DOTALL)
            reject_match = re.search(r"REJECT[:\s]+(.+?)(?=WARNING|$)", rule_content, re.IGNORECASE | re.DOTALL)

            if warning_match:
                severity_warning = warning_match.group(1).strip()[:200]
            if reject_match:
                severity_reject = reject_match.group(1).strip()[:200]

            rule = Rule(
                id=rule_id,
                title=title,
                content=rule_content,
                severity_warning=severity_warning,
                severity_reject=severity_reject,
            )
            self.rules.append(rule)
            logger.debug(f"Parsed rule: {rule_id} - {title}")

    def get_rule_by_id(self, rule_id: str) -> Rule | None:
        """
        Retrieve a specific rule by its ID.

        Args:
            rule_id: The rule identifier (e.g., "DQ-01").

        Returns:
            The Rule object if found, None otherwise.
        """
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def get_all_rules_text(self) -> str:
        """
        Get the complete text of all rules.

        Returns:
            Combined text of all rule files.
        """
        return self.rules_text

    def get_rules_summary(self) -> list[dict[str, str]]:
        """
        Get a summary of all loaded rules.

        Returns:
            List of dictionaries with rule IDs and titles.
        """
        return [{"id": rule.id, "title": rule.title} for rule in self.rules]

    def search_rules(self, keyword: str) -> list[Rule]:
        """
        Search for rules containing a specific keyword.

        Args:
            keyword: The keyword to search for.

        Returns:
            List of matching Rule objects.
        """
        keyword_lower = keyword.lower()
        matches = []

        for rule in self.rules:
            if keyword_lower in rule.content.lower() or keyword_lower in rule.title.lower():
                matches.append(rule)

        logger.debug(f"Found {len(matches)} rules matching '{keyword}'")
        return matches
