"""Issue and PR staleness detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from elasticsearch import AsyncElasticsearch

from repoman.elasticsearch.constants import ISSUES_INDEX


@dataclass(slots=True)
class StaleCounts:
    stale_issues_count: int
    stale_prs_count: int


def is_stale(updated_at: datetime, *, now: datetime | None = None, threshold_days: int = 30) -> bool:
    now_dt = now or datetime.now(tz=UTC)
    return (now_dt - updated_at) >= timedelta(days=threshold_days)


def days_open(*, created_at: datetime, closed_at: datetime | None, now: datetime | None = None) -> int:
    end = closed_at or (now or datetime.now(tz=UTC))
    return max(int((end - created_at).total_seconds() // 86400), 0)


async def query_stale_counts(
    es: AsyncElasticsearch,
    *,
    repo_full_name: str,
    threshold_days: int = 30,
) -> StaleCounts:
    """Compute stale open issues/PR counts via Elasticsearch."""
    cutoff = f"now-{threshold_days}d/d"

    common_filter = [
        {"term": {"repo_full_name": repo_full_name}},
        {"term": {"state": "open"}},
        {"range": {"updated_at": {"lt": cutoff}}},
    ]

    issues_count = await es.count(
        index=ISSUES_INDEX,
        query={
            "bool": {
                "filter": common_filter + [{"term": {"is_pull_request": False}}],
            }
        },
    )
    prs_count = await es.count(
        index=ISSUES_INDEX,
        query={
            "bool": {
                "filter": common_filter + [{"term": {"is_pull_request": True}}],
            }
        },
    )

    return StaleCounts(
        stale_issues_count=int(issues_count.get("count", 0)),
        stale_prs_count=int(prs_count.get("count", 0)),
    )
