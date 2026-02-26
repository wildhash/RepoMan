"""Analysis endpoints powered by Elasticsearch."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from repoman.api.schemas import AnalyzeRepoRequest, AnalyzeRepoResponse
from repoman.config import Settings
from repoman.elasticsearch.ingestion import ElasticsearchIngestionService

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


def _get_es(request: Request):
    es = getattr(request.app.state, "elasticsearch", None)
    if es is None:
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch is not configured. Set ELASTICSEARCH_URL and restart.",
        )
    return es


@router.post("/repo", response_model=AnalyzeRepoResponse)
async def analyze_repo(request: Request, body: AnalyzeRepoRequest) -> AnalyzeRepoResponse:
    """Run repo analysis and store results in `repoman-analysis`.

    Example:
        `POST /api/analyze/repo` with `{ "repo_full_name": "wildhash/RepoMan" }`
    """
    es = _get_es(request)
    config: Settings = request.app.state.config

    service = ElasticsearchIngestionService(config, es=es)
    try:
        analysis_doc = await service.analyze_repo(body.repo_full_name)
        analyzed_at = analysis_doc.get("analyzed_at") or datetime.now(tz=UTC).isoformat()
        return AnalyzeRepoResponse(
            repo_full_name=body.repo_full_name,
            analyzed_at=analyzed_at,
            analysis=analysis_doc,
        )
    finally:
        await service.aclose()
