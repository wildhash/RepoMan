"""Aggregation endpoints (dashboards) powered by Elasticsearch."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from repoman.elasticsearch.constants import ANALYSIS_DATA_STREAM, ISSUES_INDEX, REPOSITORIES_INDEX

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_es(request: Request):
    es = getattr(request.app.state, "elasticsearch", None)
    if es is None:
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch is not configured. Set ELASTICSEARCH_URL and restart.",
        )
    return es


@router.get("/repo-health")
async def repo_health_distribution(request: Request) -> dict:
    """Histogram of `health_score` across repositories."""
    es = _get_es(request)
    resp = await es.search(
        index=REPOSITORIES_INDEX,
        size=0,
        aggs={
            "health": {
                "histogram": {
                    "field": "health_score",
                    "interval": 10,
                    "min_doc_count": 0,
                }
            }
        },
    )
    return {"buckets": (resp.get("aggregations") or {}).get("health", {}).get("buckets", [])}


@router.get("/top-languages")
async def top_languages(request: Request) -> dict:
    """Top languages across indexed repos."""
    es = _get_es(request)
    resp = await es.search(
        index=REPOSITORIES_INDEX,
        size=0,
        aggs={"languages": {"terms": {"field": "language", "size": 20}}},
    )
    return {"buckets": (resp.get("aggregations") or {}).get("languages", {}).get("buckets", [])}


@router.get("/common-missing-elements")
async def common_missing_elements(request: Request) -> dict:
    """Most common missing elements, aggregated from `repoman-analysis` docs."""
    es = _get_es(request)
    resp = await es.search(
        index=ANALYSIS_DATA_STREAM,
        size=0,
        aggs={"missing": {"terms": {"field": "missing_elements", "size": 20}}},
    )
    return {"buckets": (resp.get("aggregations") or {}).get("missing", {}).get("buckets", [])}


@router.get("/issue-staleness-trend")
async def issue_staleness_trend(request: Request) -> dict:
    """Date histogram over `updated_at` for stale open issues/PRs."""
    es = _get_es(request)
    resp = await es.search(
        index=ISSUES_INDEX,
        size=0,
        query={"term": {"is_stale": True}},
        aggs={
            "trend": {
                "date_histogram": {
                    "field": "updated_at",
                    "calendar_interval": "week",
                }
            }
        },
    )
    return {"buckets": (resp.get("aggregations") or {}).get("trend", {}).get("buckets", [])}


@router.get("/avg-time-to-close")
async def avg_time_to_close(request: Request) -> dict:
    """Average days-to-close by repo (issues and PRs combined)."""
    es = _get_es(request)
    resp = await es.search(
        index=ISSUES_INDEX,
        size=0,
        query={"term": {"state": "closed"}},
        aggs={
            "by_repo": {
                "terms": {"field": "repo_full_name", "size": 20},
                "aggs": {"avg_days": {"avg": {"field": "days_open"}}},
            }
        },
    )
    return {"buckets": (resp.get("aggregations") or {}).get("by_repo", {}).get("buckets", [])}
