"""Main pipeline orchestrator — thin wrapper around Pipeline."""

from __future__ import annotations

from repoman.config import Settings
from repoman.core.pipeline import Pipeline
from repoman.core.state import PipelineResult


class Orchestrator:
    """Top-level orchestrator that manages pipeline lifecycle."""

    def __init__(self, config: Settings | None = None) -> None:
        """Initialise the orchestrator.

        Args:
            config: Application settings. Defaults to Settings().
        """
        self._config = config or Settings()
        self._pipeline = Pipeline(self._config)

    async def transform(self, repo_url: str) -> PipelineResult:
        """Run the full transformation pipeline.

        Args:
            repo_url: Git repository URL to transform.

        Returns:
            PipelineResult with all phases completed.
        """
        return await self._pipeline.run(repo_url)
