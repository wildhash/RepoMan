"""Search endpoints powered by Elasticsearch."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from repoman.api.schemas import SearchHit, SearchResponse, SemanticSearchRequest
from repoman.elasticsearch.queries import (
    issue_full_text_search,
    issue_semantic_search,
    repo_full_text_search,
    repo_semantic_search,
)

router = APIRouter(prefix="/api/search", tags=["search"])


def _get_es(request: Request):
    es = getattr(request.app.state, "elasticsearch", None)
    if es is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Elasticsearch is not configured. Set ELASTICSEARCH_URL (or ELASTICSEARCH_CLOUD_ID) and restart."
            ),
        )
    return es


@router.get("/repositories", response_model=SearchResponse)
async def search_repositories(
    request: Request,
    q: str = Query(..., description="Query string (full-text)"),
    language: str | None = Query(None, description="Filter by primary language"),
    status: str | None = Query(
        None, description="Filter by status (active/stale/abandoned/needs_attention)"
    ),
    has_readme: bool | None = Query(None, description="Filter by README presence"),
    health_score_min: float | None = Query(None, description="Minimum health score"),
    health_score_max: float | None = Query(None, description="Maximum health score"),
    size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    """Full-text search repositories.

    Example:
        `GET /api/search/repositories?q=agent&language=Python&health_score_min=60`
    """
    es = _get_es(request)
    body = repo_full_text_search(
        q,
        language=language,
        status=status,
        has_readme=has_readme,
        health_score_min=health_score_min,
        health_score_max=health_score_max,
        size=size,
    )
    resp = await es.search(**body)
    hits_obj = resp.get("hits") or {}
    hits = hits_obj.get("hits") or []
    total = hits_obj.get("total")
    total_value = 0
    if isinstance(total, dict):
        value = total.get("value")
        if isinstance(value, (int, float)):
            total_value = int(value)
    elif isinstance(total, (int, float)):
        total_value = int(total)

    return SearchResponse(
        total=total_value,
        hits=[
            SearchHit(
                id=h.get("_id"),
                score=h.get("_score"),
                source=h.get("_source") or {},
                highlight=h.get("highlight"),
            )
            for h in hits
        ],
    )


@router.get("/issues", response_model=SearchResponse)
async def search_issues(
    request: Request,
    q: str = Query(..., description="Query string (full-text)"),
    repo_full_name: str | None = Query(None, description="Filter by repo full name"),
    state: str | None = Query(None, description="Filter by state (open/closed)"),
    is_pull_request: bool | None = Query(None, description="Filter issues vs PRs"),
    size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    """Full-text search issues and pull requests.

    Example:
        `GET /api/search/issues?q=timeout&repo_full_name=wildhash/RepoMan&state=open`
    """
    es = _get_es(request)
    body = issue_full_text_search(
        q,
        repo_full_name=repo_full_name,
        state=state,
        is_pull_request=is_pull_request,
        size=size,
    )
    resp = await es.search(**body)
    hits_obj = resp.get("hits") or {}
    hits = hits_obj.get("hits") or []
    total = hits_obj.get("total")
    total_value = 0
    if isinstance(total, dict):
        value = total.get("value")
        if isinstance(value, (int, float)):
            total_value = int(value)
    elif isinstance(total, (int, float)):
        total_value = int(total)

    return SearchResponse(
        total=total_value,
        hits=[
            SearchHit(
                id=h.get("_id"),
                score=h.get("_score"),
                source=h.get("_source") or {},
                highlight=h.get("highlight"),
            )
            for h in hits
        ],
    )


@router.post("/semantic/repositories", response_model=SearchResponse)
async def semantic_search_repositories(
    request: Request, body: SemanticSearchRequest
) -> SearchResponse:
    """Semantic repository search using kNN over `description_embedding`.

    Example:
        `POST /api/search/semantic/repositories` with JSON body `{ "query": "vector database" }`
    """
    es = _get_es(request)
    encoder = request.app.state.encoder
    vector = encoder.encode(body.query)
    q = repo_semantic_search(vector, k=body.k)
    resp = await es.search(**q)
    hits_obj = resp.get("hits") or {}
    hits = hits_obj.get("hits") or []
    total = hits_obj.get("total")
    total_value = 0
    if isinstance(total, dict):
        value = total.get("value")
        if isinstance(value, (int, float)):
            total_value = int(value)
    elif isinstance(total, (int, float)):
        total_value = int(total)

    return SearchResponse(
        total=total_value,
        hits=[
            SearchHit(
                id=h.get("_id"),
                score=h.get("_score"),
                source=h.get("_source") or {},
                highlight=h.get("highlight"),
            )
            for h in hits
        ],
    )


@router.post("/semantic/issues", response_model=SearchResponse)
async def semantic_search_issues(request: Request, body: SemanticSearchRequest) -> SearchResponse:
    """Semantic issue search using kNN over `body_embedding`.

    Example:
        `POST /api/search/semantic/issues` with JSON body `{ "query": "CI failing on python 3.12" }`
    """
    es = _get_es(request)
    encoder = request.app.state.encoder
    vector = encoder.encode(body.query)
    q = issue_semantic_search(vector, repo_full_name=body.repo_full_name, k=body.k)
    resp = await es.search(**q)
    hits_obj = resp.get("hits") or {}
    hits = hits_obj.get("hits") or []
    total = hits_obj.get("total")
    total_value = 0
    if isinstance(total, dict):
        value = total.get("value")
        if isinstance(value, (int, float)):
            total_value = int(value)
    elif isinstance(total, (int, float)):
        total_value = int(total)

    return SearchResponse(
        total=total_value,
        hits=[
            SearchHit(
                id=h.get("_id"),
                score=h.get("_score"),
                source=h.get("_source") or {},
                highlight=h.get("highlight"),
            )
            for h in hits
        ],
    )
