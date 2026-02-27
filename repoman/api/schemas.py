"""API Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TransformRequest(BaseModel):
    """Request body for the transform endpoint."""

    repo_url: str


class TransformResponse(BaseModel):
    """Response body for the transform endpoint."""

    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Response body for the job status endpoint."""

    job_id: str
    status: str
    error: str | None = None
    before_score: float = 0.0
    after_score: float = 0.0
    issues_fixed: int = 0
    total_duration_seconds: float = 0.0


class SearchHit(BaseModel):
    """Single Elasticsearch search hit."""

    id: str | None = None
    score: float | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    highlight: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    """Elasticsearch search response wrapper."""

    total: int
    hits: list[SearchHit]


class SemanticSearchRequest(BaseModel):
    """Request body for semantic (kNN) search endpoints."""

    query: str
    repo_full_name: str | None = None
    k: int = 10


class AnalyzeRepoRequest(BaseModel):
    """Request body to trigger analysis for a repo."""

    repo_full_name: str


class AnalyzeRepoResponse(BaseModel):
    """Response body returned after indexing an analysis document."""

    repo_full_name: str
    analyzed_at: str
    analysis: dict[str, Any]
