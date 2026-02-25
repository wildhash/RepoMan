"""Job status routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from repoman.api.schemas import JobStatusResponse
from repoman.core.state import PipelineResult

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, request: Request) -> JobStatusResponse:
    """Get the status and result of a pipeline job.

    Args:
        job_id: Unique job identifier.
        request: The incoming request.

    Returns:
        JobStatusResponse with current status and scores.

    Raises:
        HTTPException: 404 if the job is not found.
    """
    jobs: dict = request.app.state.jobs
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result: PipelineResult | None = job.get("result")
    if result:
        return JobStatusResponse(
            job_id=job_id,
            status=result.status.value,
            error=result.error,
            before_score=result.before_score,
            after_score=result.after_score,
            issues_fixed=result.issues_fixed,
            total_duration_seconds=result.total_duration_seconds,
        )

    return JobStatusResponse(job_id=job_id, status=job["status"].value)


@router.get("/{job_id}/transcript")
async def get_transcript(job_id: str, request: Request) -> dict:
    """Get the debate transcript for a completed job.

    Args:
        job_id: Unique job identifier.
        request: The incoming request.

    Returns:
        Dict with transcript list.

    Raises:
        HTTPException: 404 if the job is not found.
    """
    jobs: dict = request.app.state.jobs
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result: PipelineResult | None = job.get("result")
    if result and result.consensus:
        return {"transcript": [m.model_dump(mode="json") for m in result.consensus.transcript]}
    return {"transcript": []}
