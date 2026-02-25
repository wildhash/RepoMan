"""ChromaDB-backed knowledge base for self-learning."""

from __future__ import annotations

import json

import structlog

from repoman.config import Settings
from repoman.core.state import PipelineResult

log = structlog.get_logger()


class KnowledgeBase:
    """Persistent vector store for patterns and strategies using ChromaDB."""

    def __init__(self, config: Settings) -> None:
        """Initialise the knowledge base.

        Args:
            config: Application settings with knowledge_base_path.
        """
        self._config = config
        self._client = None
        self._patterns = None
        self._strategies = None
        self._setup()

    def _setup(self) -> None:
        """Initialise the ChromaDB client and collections."""
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=self._config.knowledge_base_path)
            self._patterns = self._client.get_or_create_collection("patterns")
            self._strategies = self._client.get_or_create_collection("strategies")
        except Exception as exc:
            log.warning("knowledge_base_init_failed", error=str(exc))

    def learn_from_run(self, result: PipelineResult) -> None:
        """Store patterns and strategies from a completed pipeline run.

        Args:
            result: Completed pipeline result to learn from.
        """
        if not self._patterns or not self._strategies:
            return
        try:
            for report in result.audit_reports:
                for issue in report.critical_issues + report.major_issues:
                    self._patterns.upsert(
                        ids=[issue.id],
                        documents=[issue.description],
                        metadatas=[{
                            "language": result.before_snapshot.primary_language if result.before_snapshot else "",
                            "category": issue.category,
                            "severity": issue.severity,
                            "suggested_fix": issue.suggested_fix,
                            "success": result.status.value == "completed",
                        }],
                    )

            if result.consensus and result.after_score > result.before_score:
                plan_str = json.dumps(result.consensus.unified_plan, default=str)
                self._strategies.upsert(
                    ids=[result.job_id],
                    documents=[plan_str],
                    metadatas=[{
                        "language": result.before_snapshot.primary_language if result.before_snapshot else "",
                        "score_improvement": result.after_score - result.before_score,
                        "issues_fixed": result.issues_fixed,
                    }],
                )
        except Exception as exc:
            log.warning("learn_from_run_failed", error=str(exc))

    def get_relevant_patterns(self, language: str, issues: list, n: int = 10) -> list[dict]:
        """Retrieve relevant past patterns via semantic search.

        Args:
            language: Primary language of the current repo.
            issues: Current issues to find similar patterns for.
            n: Number of results to return.

        Returns:
            List of pattern dicts with description and metadata.
        """
        if not self._patterns or not issues:
            return []
        try:
            query = " ".join(getattr(i, "description", str(i)) for i in issues[:5])
            results = self._patterns.query(
                query_texts=[query],
                n_results=min(n, 10),
                where={"language": language} if language else None,
            )
            patterns = []
            for doc, meta in zip(
                results.get("documents", [[]])[0],
                results.get("metadatas", [[]])[0],
            ):
                patterns.append({"description": doc, **meta})
            return patterns
        except Exception as exc:
            log.warning("get_patterns_failed", error=str(exc))
            return []
