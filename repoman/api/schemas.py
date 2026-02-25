"""API Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


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
