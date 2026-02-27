"""Strategy optimisation using historical knowledge."""

from __future__ import annotations

from repoman.learning.knowledge_base import KnowledgeBase


class StrategyOptimizer:
    """Refines agent strategies using past run data."""

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        """Initialise the optimiser.

        Args:
            knowledge_base: Knowledge base instance.
        """
        self._kb = knowledge_base

    def get_enhanced_context(self, language: str, issues: list) -> str:
        """Build an enhanced context string from past patterns.

        Args:
            language: Primary programming language.
            issues: Current issues to search for.

        Returns:
            Context string to inject into agent prompts.
        """
        patterns = self._kb.get_relevant_patterns(language, issues)
        if not patterns:
            return ""
        lines = ["Relevant patterns from past runs:"]
        for p in patterns[:5]:
            lines.append(
                f"- [{p.get('severity', '?')}] {p.get('description', '')}: {p.get('suggested_fix', '')}"
            )
        return "\n".join(lines)
