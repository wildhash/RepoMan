"""CI/CD and Dockerfile generation."""

from __future__ import annotations

from repoman.core.state import RepoSnapshot
from repoman.models.router import ModelRouter


class CICDGenerator:
    """Generates GitHub Actions workflows and Dockerfiles."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the CI/CD generator.

        Args:
            router: Model router instance.
        """
        self._router = router

    async def generate_github_actions(self, snapshot: RepoSnapshot) -> str:
        """Generate a GitHub Actions CI workflow.

        Args:
            snapshot: Repository snapshot.

        Returns:
            YAML workflow content.
        """
        from repoman.models.base import Message

        prompt = f"""Generate a GitHub Actions CI workflow for this repository.

Language: {snapshot.primary_language}
Frameworks: {", ".join(snapshot.frameworks)}
Has tests: {snapshot.has_tests}

Return only the YAML content for .github/workflows/ci.yml."""

        messages = [Message(role="user", content=prompt)]
        response = await self._router.complete("builder", messages)
        return response.content

    async def generate_dockerfile(self, snapshot: RepoSnapshot) -> str:
        """Generate a production Dockerfile.

        Args:
            snapshot: Repository snapshot.

        Returns:
            Dockerfile content.
        """
        from repoman.models.base import Message

        prompt = f"""Generate a production-ready Dockerfile for this repository.

Language: {snapshot.primary_language}
Entry points: {", ".join(snapshot.entry_points)}

Use multi-stage build if appropriate. Return only the Dockerfile content."""

        messages = [Message(role="user", content=prompt)]
        response = await self._router.complete("builder", messages)
        return response.content
