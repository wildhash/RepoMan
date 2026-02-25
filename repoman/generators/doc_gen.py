"""Documentation generation."""

from __future__ import annotations

from repoman.core.state import RepoSnapshot
from repoman.models.router import ModelRouter


class DocGenerator:
    """Generates README, docstrings, and API documentation."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the doc generator.

        Args:
            router: Model router instance.
        """
        self._router = router

    async def generate_readme(self, snapshot: RepoSnapshot) -> str:
        """Generate a comprehensive README for a repository.

        Args:
            snapshot: Repository snapshot.

        Returns:
            README markdown content.
        """
        from repoman.models.base import Message

        prompt = f"""Generate a comprehensive README.md for this repository.

Repository: {snapshot.name}
Language: {snapshot.primary_language}
Frameworks: {', '.join(snapshot.frameworks)}
Entry points: {', '.join(snapshot.entry_points)}
Has tests: {snapshot.has_tests}
Has CI: {snapshot.has_ci}

Include: overview, features, installation, usage, development setup, contributing, license.
Return only the markdown content."""

        messages = [Message(role="user", content=prompt)]
        response = await self._router.complete("builder", messages)
        return response.content
