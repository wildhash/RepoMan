"""Integration tests for the full pipeline (require real API keys)."""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Requires real LLM API keys and network access")
async def test_full_pipeline_on_broken_repo() -> None:
    """Full pipeline integration test — skipped without API keys."""
    from repoman.config import Settings
    from repoman.core.pipeline import Pipeline

    settings = Settings()
    if not settings.anthropic_api_key or not settings.openai_api_key:
        pytest.skip("API keys not configured")

    pipeline = Pipeline(settings)
    result = await pipeline.run("https://github.com/test/broken-repo")
    assert result.status.value in ("completed", "failed")
    assert result.job_id
