"""Repository transformation routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Request

from repoman.api.schemas import TransformRequest, TransformResponse
from repoman.core.pipeline import Pipeline
from repoman.core.state import JobStatus, PipelineResult

router = APIRouter(prefix="/api/repos", tags=["repos"])


@router.post("/transform", response_model=TransformResponse)
async def transform_repo(
    body: TransformRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> TransformResponse:
    """Enqueue a repository transformation job.

    Args:
        body: Request with repo_url.
        background_tasks: FastAPI background task runner.
        request: The incoming request (used to access app state).

    Returns:
        TransformResponse with job_id and status.
    """
    job_id = str(uuid.uuid4())
    jobs: dict = request.app.state.jobs
    jobs[job_id] = {"status": JobStatus.queued, "result": None}

    config = request.app.state.config
    pipeline = Pipeline(config, event_bus=getattr(request.app.state, "event_bus", None))

    async def run_pipeline() -> None:
        jobs[job_id]["status"] = JobStatus.running
        result: PipelineResult = await pipeline.run(body.repo_url, job_id=job_id)
        jobs[job_id]["status"] = result.status
        jobs[job_id]["result"] = result

    background_tasks.add_task(run_pipeline)
    return TransformResponse(job_id=job_id, status=JobStatus.queued.value)
