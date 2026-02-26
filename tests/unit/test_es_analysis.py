"""Unit tests for Elasticsearch-powered analysis helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from repoman.analysis.completeness import compute_completeness
from repoman.analysis.direction import assess_repo_direction
from repoman.analysis.duplicates import find_duplicate_issue_groups
from repoman.analysis.recommendations import generate_action_items
from repoman.analysis.staleness import is_stale, query_stale_counts


class TestCompleteness:
    def test_full_completeness(self) -> None:
        result = compute_completeness(
            readme_text="x" * 600,
            has_license=True,
            has_contributing=True,
            has_ci_config=True,
            has_tests=True,
            has_package_manager_config=True,
        )
        assert result.missing_elements == []
        assert result.completeness_score == pytest.approx(100.0)

    def test_missing_elements(self) -> None:
        result = compute_completeness(
            readme_text=None,
            has_license=False,
            has_contributing=True,
            has_ci_config=False,
            has_tests=True,
            has_package_manager_config=False,
        )
        assert set(result.missing_elements) == {"README", "LICENSE", "CI_CONFIG", "PACKAGE_MANAGER"}
        assert 0.0 < result.completeness_score < 100.0


class TestStaleness:
    def test_is_stale_true(self) -> None:
        now = datetime.now(tz=UTC)
        assert is_stale(now - timedelta(days=31), now=now, threshold_days=30) is True

    @pytest.mark.asyncio
    async def test_query_stale_counts(self) -> None:
        es = AsyncMock()
        es.count = AsyncMock(side_effect=[{"count": 2}, {"count": 1}])
        result = await query_stale_counts(es, repo_full_name="o/r", threshold_days=30)
        assert result.stale_issues_count == 2
        assert result.stale_prs_count == 1
        assert es.count.call_count == 2


class TestDuplicates:
    @pytest.mark.asyncio
    async def test_find_duplicate_issue_groups(self) -> None:
        es = AsyncMock()

        issue_a = {"issue_id": "A", "body_embedding": [0.1] * 384}
        issue_b = {"issue_id": "B", "body_embedding": [0.2] * 384}
        issue_c = {"issue_id": "C", "body_embedding": [0.3] * 384}

        es.search = AsyncMock(
            side_effect=[
                {
                    "hits": {
                        "hits": [
                            {"_source": issue_a},
                            {"_source": issue_b},
                            {"_source": issue_c},
                        ]
                    }
                },
                {"hits": {"hits": [{"_source": {"issue_id": "B"}, "_score": 0.9}]}},
                {"hits": {"hits": [{"_source": {"issue_id": "A"}, "_score": 0.9}]}},
                {"hits": {"hits": []}},
            ]
        )

        groups = await find_duplicate_issue_groups(es, repo_full_name="o/r", threshold=0.85)
        assert len(groups) == 1
        assert groups[0].issue_ids == ["A", "B"]
        assert groups[0].representative_issue_id == "A"


class TestDirectionAndRecommendations:
    @pytest.mark.asyncio
    async def test_direction_diverges(self) -> None:
        es = AsyncMock()
        es.search = AsyncMock(
            return_value={
                "hits": {
                    "hits": [
                        {"_source": {"labels": ["ui", "frontend"], "title": "Add UI"}},
                        {"_source": {"labels": ["ui"], "title": "Improve UI"}},
                    ]
                }
            }
        )

        assessment = await assess_repo_direction(
            es,
            repo_full_name="o/r",
            repo_topics=["cli"],
            repo_description="A CLI tool",
        )
        assert assessment.diverges is True
        assert "Recent closed work labels" in assessment.summary

    def test_generate_action_items(self) -> None:
        items = generate_action_items(
            missing_elements=["README", "CI_CONFIG"],
            stale_issues_count=3,
            stale_prs_count=0,
            duplicate_groups=[],
            direction_diverges=False,
        )
        priorities = {i.priority for i in items}
        assert "critical" in priorities
        assert any("stale" in i.description.lower() for i in items)
