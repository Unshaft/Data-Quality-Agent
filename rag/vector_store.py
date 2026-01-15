"""
Vector Store module for semantic rule retrieval.
Uses ChromaDB with sentence-transformers embeddings.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from rag.rules_loader import Rule

logger = logging.getLogger(__name__)


class VectorRulesStore:
    """
    Manages vector embeddings of quality rules for semantic retrieval.

    This class bridges the knowledge layer with the decision layer by
    enabling context-aware rule retrieval based on detected data issues.
    """

    COLLECTION_NAME = "dq_rules"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, lightweight, effective

    def __init__(self, persist_directory: str | Path = ".chroma"):
        """
        Initialize the vector store.

        Args:
            persist_directory: Directory for ChromaDB persistence.
        """
        self.persist_directory = Path(persist_directory)
        logger.info(f"Initializing VectorRulesStore at {self.persist_directory}")

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))

        # Use sentence-transformers for embeddings (local, no API key needed)
        logger.info(f"Loading embedding model: {self.EMBEDDING_MODEL}")
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.EMBEDDING_MODEL
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"description": "Data Quality Rules for RAG"}
        )

        logger.info(f"VectorRulesStore initialized with {self.collection.count()} existing rules")

    def index_rules(self, rules: list[Rule], force_reindex: bool = False) -> int:
        """
        Index rules into the vector store.

        Args:
            rules: List of Rule objects to index.
            force_reindex: If True, clear existing and reindex all.

        Returns:
            Number of rules indexed.
        """
        logger.info(f"Indexing {len(rules)} rules (force_reindex={force_reindex})")

        if force_reindex:
            logger.info("Force reindex: deleting existing collection")
            self.client.delete_collection(self.COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self.embedding_fn,
                metadata={"description": "Data Quality Rules for RAG"}
            )

        # Skip if already indexed with same count
        if self.collection.count() >= len(rules) and not force_reindex:
            logger.info(f"Rules already indexed ({self.collection.count()} rules), skipping")
            return self.collection.count()

        # Prepare documents for indexing
        documents = []
        metadatas = []
        ids = []

        for rule in rules:
            # Create rich document text for better semantic matching
            doc_text = f"""Rule ID: {rule.id}
Title: {rule.title}

Description:
{rule.content}

Warning Condition: {rule.severity_warning or 'Not specified'}
Reject Condition: {rule.severity_reject or 'Not specified'}"""

            documents.append(doc_text)
            metadatas.append({
                "rule_id": rule.id,
                "title": rule.title,
                "has_warning": rule.severity_warning is not None,
                "has_reject": rule.severity_reject is not None,
            })
            ids.append(rule.id)

        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Successfully indexed {len(rules)} rules into vector store")
        return len(rules)

    def search_relevant_rules(
        self,
        query: str,
        n_results: int = 3
    ) -> list[dict[str, Any]]:
        """
        Search for rules relevant to a given query/issue.

        Args:
            query: Description of the data quality issue.
            n_results: Maximum number of rules to return.

        Returns:
            List of matching rules with metadata and relevance scores.
        """
        logger.debug(f"Searching rules for: {query[:50]}...")

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        relevant_rules = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                relevant_rules.append({
                    "rule_id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],  # Lower = more relevant
                })

        logger.debug(f"Found {len(relevant_rules)} relevant rules")
        return relevant_rules

    def get_rules_for_issue_type(self, issue_type: str) -> list[dict[str, Any]]:
        """
        Get rules relevant to a specific issue type.

        Args:
            issue_type: Type of issue (e.g., "missing values", "outliers").

        Returns:
            Relevant rules sorted by relevance.
        """
        query = f"Data quality issue: {issue_type}. What rules apply?"
        return self.search_relevant_rules(query)

    def get_all_rules_text(self) -> str:
        """
        Get concatenated text of all indexed rules.

        Returns:
            Combined text of all rules.
        """
        all_docs = self.collection.get(include=["documents"])
        if all_docs["documents"]:
            return "\n\n---\n\n".join(all_docs["documents"])
        return ""
