"""
Data Quality Agent - Main Entry Point

This script orchestrates the complete data quality analysis pipeline:
1. Load and profile a dataset
2. Load quality rules
3. Run the quality agent (V1 rule-based or V2 LLM-powered)
4. Output a structured decision report

Usage:
    python main.py [--data PATH] [--rules PATH] [--output PATH] [--verbose]

    # V2 mode (LLM-powered with Claude)
    python main.py --v2 --data data/sample.csv

    # Batch mode (analyze multiple files)
    python main.py --batch data/test/ --format html

Example:
    python main.py --data data/sample.csv --rules rules/ --output reports/report.json
    python main.py --v2 --data data/test/missing_warning.csv --verbose
    python main.py --batch data/test/ --format both
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from profiling import DataProfiler
from rag import RulesLoader
from agent import QualityAgent
from reports import ReportExporter


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: If True, set DEBUG level; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter with UTF-8 safe output
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Set encoding for Windows compatibility
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    root_logger.addHandler(console_handler)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Data Quality Agent - Analyze dataset quality with AI-powered reasoning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # V1 (rule-based, no API key needed)
  python main.py --data data/test/clean.csv

  # V2 (LLM-powered with Claude)
  python main.py --v2 --data data/test/missing_warning.csv

  # V2 with specific model
  python main.py --v2 --model claude-3-haiku-20240307 --data data/test/clean.csv

  # Batch mode - analyze all CSV files in a directory
  python main.py --batch data/test/ --format html

  # Export to both JSON and HTML
  python main.py --data data/test/clean.csv --output reports/ --format both
        """,
    )

    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path to the CSV dataset to analyze",
    )

    parser.add_argument(
        "--rules",
        type=str,
        default="rules",
        help="Path to the directory containing quality rules (default: rules)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save the report (directory for batch mode)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    # V2 arguments
    parser.add_argument(
        "--v2",
        action="store_true",
        help="Use V2 LLM-powered agent (requires ANTHROPIC_API_KEY in .env)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Claude model for V2 (default: claude-sonnet-4-20250514)",
    )

    # Batch mode
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Directory containing multiple CSV files to analyze",
    )

    # Export format
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "html", "both"],
        default="json",
        help="Output format for reports (default: json)",
    )

    return parser.parse_args()


def analyze_single_file(
    data_path: Path,
    rules_loader: RulesLoader,
    args: argparse.Namespace,
    logger: logging.Logger,
):
    """
    Analyze a single dataset file.

    Args:
        data_path: Path to the CSV file.
        rules_loader: Loaded RulesLoader instance.
        args: Command line arguments.
        logger: Logger instance.

    Returns:
        QualityReport for the analyzed file.
    """
    version = "V2 (LLM-powered)" if args.v2 else "V1 (rule-based)"

    # Profile the data
    profiler = DataProfiler(data_path)
    profile = profiler.generate_profile()

    logger.info(f"Profiled: {profile['basic_stats']['row_count']} rows, {profile['basic_stats']['column_count']} columns")

    # Create and run agent
    if args.v2:
        from agent import LLMQualityAgent
        from rag import VectorRulesStore

        vector_store = VectorRulesStore()
        vector_store.index_rules(rules_loader.rules)

        agent = LLMQualityAgent(
            vector_store=vector_store,
            model_name=args.model,
        )
    else:
        agent = QualityAgent(rules_loader)

    return agent.analyze(profile)


def run_batch_analysis(args: argparse.Namespace) -> int:
    """
    Run batch analysis on multiple files.

    Args:
        args: Command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger = logging.getLogger(__name__)
    version = "V2 (LLM-powered)" if args.v2 else "V1 (rule-based)"

    logger.info("=" * 70)
    logger.info(f"DATA QUALITY AGENT {version} - Batch Analysis")
    logger.info("=" * 70)

    batch_dir = Path(args.batch)
    if not batch_dir.exists():
        logger.error(f"Batch directory not found: {batch_dir}")
        return 1

    # Find all CSV files
    csv_files = list(batch_dir.glob("*.csv"))
    if not csv_files:
        logger.error(f"No CSV files found in: {batch_dir}")
        return 1

    logger.info(f"Found {len(csv_files)} CSV files to analyze")

    # Load rules once
    rules_path = Path(args.rules)
    rules_loader = RulesLoader(rules_path)
    rules_loader.load_rules()
    logger.info(f"Loaded {len(rules_loader.rules)} quality rules")

    # Initialize exporter
    output_dir = Path(args.output) if args.output else Path("reports/batch")
    exporter = ReportExporter(output_dir)

    # Analyze each file
    results: list[tuple[str, any]] = []

    for i, csv_file in enumerate(csv_files, 1):
        logger.info("-" * 70)
        logger.info(f"[{i}/{len(csv_files)}] Analyzing: {csv_file.name}")

        try:
            report = analyze_single_file(csv_file, rules_loader, args, logger)
            results.append((csv_file.name, report))

            # Export individual report
            base_name = csv_file.stem
            metadata = {
                "source_file": str(csv_file),
                "agent_version": version,
                "analyzed_at": datetime.now().isoformat(),
            }

            if args.format in ["json", "both"]:
                exporter.export_json(report, f"{base_name}.json", metadata)

            if args.format in ["html", "both"]:
                exporter.export_html(report, f"{base_name}.html", metadata)

            logger.info(f"  Result: {report.decision} ({len(report.issues)} issues)")

        except Exception as e:
            logger.error(f"  Error analyzing {csv_file.name}: {e}")
            continue

    # Generate batch summary
    if results:
        exporter.export_batch_summary(results)

        # Print summary
        print("\n" + "=" * 70)
        print(f"BATCH ANALYSIS COMPLETE - {len(results)}/{len(csv_files)} files processed")
        print("=" * 70)

        counts = {"ACCEPT": 0, "WARNING": 0, "REJECT": 0}
        for _, report in results:
            counts[report.decision] = counts.get(report.decision, 0) + 1

        print(f"\nSummary:")
        print(f"  ACCEPT:  {counts.get('ACCEPT', 0)}")
        print(f"  WARNING: {counts.get('WARNING', 0)}")
        print(f"  REJECT:  {counts.get('REJECT', 0)}")
        print(f"\nReports saved to: {output_dir}")
        print("=" * 70)

    logger.info("=" * 70)
    logger.info("Batch analysis complete")
    logger.info("=" * 70)

    return 0


def run_single_analysis(args: argparse.Namespace) -> int:
    """
    Run analysis on a single file.

    Args:
        args: Command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger = logging.getLogger(__name__)
    version = "V2 (LLM-powered)" if args.v2 else "V1 (rule-based)"

    logger.info("=" * 70)
    logger.info(f"DATA QUALITY AGENT {version} - Starting Analysis")
    logger.info("=" * 70)

    # Resolve paths
    data_path = Path(args.data)
    rules_path = Path(args.rules)

    logger.info(f"Dataset path: {data_path}")
    logger.info(f"Rules path: {rules_path}")

    # =================================================================
    # STEP 1: Data Profiling (Facts Layer)
    # =================================================================
    logger.info("-" * 70)
    logger.info("STEP 1: Data Profiling")
    logger.info("-" * 70)

    profiler = DataProfiler(data_path)
    profile = profiler.generate_profile()

    logger.info(f"Profiling complete: {profile['basic_stats']['row_count']} rows, {profile['basic_stats']['column_count']} columns")

    # =================================================================
    # STEP 2: Load Quality Rules (Knowledge Layer)
    # =================================================================
    logger.info("-" * 70)
    logger.info("STEP 2: Loading Quality Rules")
    logger.info("-" * 70)

    rules_loader = RulesLoader(rules_path)
    rules = rules_loader.load_rules()

    logger.info(f"Loaded {len(rules)} quality rules")
    for rule in rules:
        logger.debug(f"  - {rule.id}: {rule.title}")

    # =================================================================
    # STEP 3: Agent Analysis (Decision Layer)
    # =================================================================
    logger.info("-" * 70)
    logger.info(f"STEP 3: Agent Analysis ({version})")
    logger.info("-" * 70)

    if args.v2:
        # V2: LLM-powered agent with Claude
        try:
            from agent import LLMQualityAgent
            from rag import VectorRulesStore
        except ImportError as e:
            logger.error(f"V2 dependencies not installed: {e}")
            logger.error("Please run: pip install -r requirements.txt")
            return 1

        # Initialize vector store and index rules
        logger.info("Initializing vector store for semantic search...")
        vector_store = VectorRulesStore()
        vector_store.index_rules(rules)

        # Create LLM agent
        logger.info("Creating LLM agent...")
        agent = LLMQualityAgent(
            vector_store=vector_store,
            model_name=args.model,
        )
    else:
        # V1: Rule-based agent
        agent = QualityAgent(rules_loader)

    report = agent.analyze(profile)

    # =================================================================
    # STEP 4: Output Results
    # =================================================================
    logger.info("-" * 70)
    logger.info("STEP 4: Results")
    logger.info("-" * 70)

    # Display results
    print("\n" + "=" * 70)
    print(f"QUALITY ANALYSIS REPORT ({version})")
    print("=" * 70)
    print(f"\nDecision: {report.decision}")
    print(f"Summary: {report.summary}")
    print(f"\nDataset Statistics:")
    print(f"  - Rows: {report.stats['row_count']:,}")
    print(f"  - Columns: {report.stats['column_count']}")
    print(f"  - Issues found: {report.stats['issues_count']}")

    if report.issues:
        print(f"\nIssues Detected ({len(report.issues)}):")
        print("-" * 50)
        for i, issue in enumerate(report.issues, 1):
            print(f"\n  [{i}] {issue.type}")
            print(f"      Severity: {issue.severity.upper()}")
            print(f"      Rule: {issue.rule_reference}")
            if issue.column:
                print(f"      Column: {issue.column}")
            print(f"      Explanation: {issue.explanation}")

    print("\n" + "=" * 70)

    # Save to file if requested
    if args.output:
        output_dir = Path(args.output)
        exporter = ReportExporter(output_dir)

        metadata = {
            "generated_at": datetime.now().isoformat(),
            "data_file": str(data_path),
            "rules_directory": str(rules_path),
            "agent_version": version,
            "model": args.model if args.v2 else "N/A (rule-based)",
        }

        base_name = data_path.stem

        if args.format in ["json", "both"]:
            exporter.export_json(report, f"{base_name}.json", metadata)

        if args.format in ["html", "both"]:
            exporter.export_html(report, f"{base_name}.html", metadata)

    logger.info("=" * 70)
    logger.info("DATA QUALITY AGENT - Analysis Complete")
    logger.info("=" * 70)

    return 0


def main() -> int:
    """
    Main entry point for the Data Quality Agent.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Parse arguments
    args = parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Batch mode
        if args.batch:
            return run_batch_analysis(args)

        # Single file mode
        if not args.data:
            # Default to a sample file
            args.data = "data/e_commerce_shopper_behaviour_and_lifestyle.csv"

        return run_single_analysis(args)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
