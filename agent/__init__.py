"""
Agent module for reasoning and decision making.

V1: QualityAgent - Rule-based with hard-coded thresholds
V2: LLMQualityAgent - Claude-powered with LangChain
"""

from .quality_agent import QualityAgent, QualityReport, Issue, Decision, Severity

# V2 imports (lazy to avoid import errors if dependencies missing)
try:
    from .llm_agent import LLMQualityAgent
    __all__ = [
        "QualityAgent",      # V1 - Rule-based
        "LLMQualityAgent",   # V2 - LLM-powered
        "QualityReport",
        "Issue",
        "Decision",
        "Severity",
    ]
except ImportError:
    # V2 dependencies not installed
    __all__ = [
        "QualityAgent",
        "QualityReport",
        "Issue",
        "Decision",
        "Severity",
    ]
