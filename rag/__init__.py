"""
RAG module for loading and consulting data quality rules.

V1: RulesLoader - Simple markdown parsing
V2: VectorRulesStore - Semantic search with ChromaDB
"""

from .rules_loader import RulesLoader, Rule

# V2 imports (lazy to avoid import errors if dependencies missing)
try:
    from .vector_store import VectorRulesStore
    __all__ = ["RulesLoader", "Rule", "VectorRulesStore"]
except ImportError:
    # V2 dependencies not installed
    __all__ = ["RulesLoader", "Rule"]
