# Data Quality Agent

An AI-powered agentic system for automated data quality assessment of tabular datasets.

## Overview

This project implements an **agentic AI system** (not ML-based) that analyzes tabular dataset quality using:
- **Measurable facts** extracted from data profiling
- **Documented rules** for quality assessment
- **Explicit reasoning** to produce justified, traceable decisions

### Key Features

- **Two analysis modes**: Rule-based (V1) and LLM-powered with Claude (V2)
- **RAG integration**: Semantic search over quality rules using ChromaDB
- **Batch processing**: Analyze multiple files at once
- **Multiple export formats**: JSON and HTML reports
- **Comprehensive testing**: 30+ unit tests with pytest

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA QUALITY AGENT                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│   │   PROFILING  │     │     RAG      │     │    AGENT     │           │
│   │    (Facts)   │     │ (Knowledge)  │     │  (Decision)  │           │
│   ├──────────────┤     ├──────────────┤     ├──────────────┤           │
│   │              │     │              │     │              │           │
│   │ • Row count  │     │ • Rules MD   │     │ • V1: Rules  │           │
│   │ • Col types  │────▶│ • ChromaDB   │────▶│ • V2: Claude │──────▶    │
│   │ • Missing %  │     │ • Semantic   │     │ • Reasoning  │   REPORT  │
│   │ • Outliers   │     │   Search     │     │ • Decision   │           │
│   │ • Negatives  │     │              │     │              │           │
│   │              │     │              │     │              │           │
│   └──────────────┘     └──────────────┘     └──────────────┘           │
│                                                                          │
│         CSV Input              Rules/*.md           ACCEPT/WARNING/REJECT│
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
Data-Quality-Agent/
├── profiling/              # Facts Layer - Data profiling
│   ├── __init__.py
│   └── profiler.py         # DataProfiler class
├── rag/                    # Knowledge Layer - Rules & RAG
│   ├── __init__.py
│   ├── rules_loader.py     # RulesLoader class
│   └── vector_store.py     # ChromaDB integration (V2)
├── agent/                  # Decision Layer - AI Agent
│   ├── __init__.py
│   ├── quality_agent.py    # V1 Rule-based agent
│   ├── llm_agent.py        # V2 LLM-powered agent
│   └── tools.py            # LangChain tools for V2
├── reports/                # Report generation
│   ├── __init__.py
│   └── exporter.py         # JSON/HTML export
├── rules/                  # Quality rules (markdown)
│   └── dq_rules.md
├── tests/                  # Unit tests
│   ├── test_profiler.py
│   ├── test_rules_loader.py
│   └── test_quality_agent.py
├── data/                   # Sample datasets
│   └── test/               # Test datasets
├── scripts/                # Utility scripts
│   └── generate_test_data.py
├── main.py                 # CLI entry point
├── requirements.txt
└── .env.example            # API key template
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Data-Quality-Agent.git
cd Data-Quality-Agent

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### V2 Setup (LLM-powered)

For V2 mode with Claude:

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

### Basic Usage (V1 - Rule-based)

```bash
# Analyze a single file
python main.py --data data/test/clean.csv

# With verbose logging
python main.py --data data/test/missing_warning.csv --verbose
```

### LLM-Powered Analysis (V2)

```bash
# Use Claude for intelligent analysis
python main.py --v2 --data data/test/clean.csv

# With a specific model
python main.py --v2 --model claude-3-haiku-20240307 --data data/test/clean.csv
```

### Batch Processing

```bash
# Analyze all CSV files in a directory
python main.py --batch data/test/ --format html

# Export both JSON and HTML reports
python main.py --batch data/test/ --format both --output reports/batch
```

### Export Options

```bash
# Export single file analysis to HTML
python main.py --data data/test/clean.csv --output reports/ --format html

# Export to both formats
python main.py --data data/test/clean.csv --output reports/ --format both
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--data` | Path to CSV file | - |
| `--batch` | Directory with multiple CSVs | - |
| `--rules` | Rules directory | `rules` |
| `--output` | Output directory | - |
| `--format` | Export format: `json`, `html`, `both` | `json` |
| `--v2` | Use LLM-powered agent | `false` |
| `--model` | Claude model for V2 | `claude-sonnet-4-20250514` |
| `--verbose` | Enable debug logging | `false` |

## Output

### Decision Types

| Decision | Meaning |
|----------|---------|
| **ACCEPT** | Dataset passes all quality checks |
| **WARNING** | Issues found but dataset usable with caution |
| **REJECT** | Critical issues, manual review required |

### Sample JSON Report

```json
{
  "decision": "WARNING",
  "summary": "Dataset has quality issues requiring attention.",
  "issues": [
    {
      "type": "Missing values",
      "severity": "medium",
      "rule_reference": "DQ-01",
      "explanation": "Column 'age' has 25.0% missing values (threshold: 20%)",
      "column": "age"
    }
  ],
  "stats": {
    "row_count": 1000,
    "column_count": 12,
    "issues_count": 1
  }
}
```

### HTML Report

The HTML reports include:
- Color-coded decision badge (green/yellow/red)
- Dataset statistics summary
- Detailed issue list with severity indicators
- Batch summary with aggregated counts

## Quality Rules

Rules are documented in `rules/dq_rules.md`:

| ID | Rule | Thresholds |
|----|------|------------|
| DQ-01 | Missing values | 20-40% → WARNING, >40% → REJECT |
| DQ-02 | Empty dataset | 0 rows → REJECT |
| DQ-03 | Data types | Unexpected type → WARNING |
| DQ-04 | Negative values | Impossible negatives → WARNING |
| DQ-05 | Outliers (IQR) | >5% outliers → WARNING |
| DQ-06 | Invalid dates | >5% invalid → WARNING |
| DQ-07 | Category consistency | Unexpected value → WARNING |
| DQ-08 | Duplicates | High duplication → WARNING |
| DQ-09 | Ratio bounds | Outside [0,1] → WARNING |
| DQ-10 | Behavioral consistency | Inconsistency → WARNING |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_profiler.py -v
```

## Technology Stack

### Core
- **Python 3.10+**
- **pandas** - Data manipulation
- **numpy** - Numerical operations

### V2 (LLM-powered)
- **LangGraph** - Agent orchestration
- **LangChain** - LLM integration
- **Anthropic Claude** - LLM reasoning
- **ChromaDB** - Vector database for RAG
- **sentence-transformers** - Local embeddings

### Testing & Quality
- **pytest** - Unit testing

## V1 vs V2 Comparison

| Feature | V1 (Rule-based) | V2 (LLM-powered) |
|---------|-----------------|------------------|
| API Key Required | No | Yes (Anthropic) |
| Speed | Fast (~1s) | Slower (~10-30s) |
| Reasoning | Hard-coded thresholds | Natural language |
| Flexibility | Fixed rules | Adaptive |
| Cost | Free | API costs |
| Best For | Production pipelines | Exploratory analysis |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Built as a demonstration of agentic AI architecture for data quality assessment.

---

**Note**: This project demonstrates key concepts in AI agent development:
- Separation of concerns (Facts → Knowledge → Decision)
- RAG (Retrieval Augmented Generation) patterns
- Tool-calling agents with LangGraph
- Explicit reasoning and traceability
