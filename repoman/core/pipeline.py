"""Seven-phase pipeline controller."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from repoman.agents.architect import ArchitectAgent
from repoman.agents.auditor import AuditorAgent
from repoman.agents.builder import BuilderAgent
from repoman.agents.orchestrator_agent import OrchestratorAgent
from repoman.analysis.ingestion import RepoIngester
from repoman.config import Settings
from repoman.consensus.engine import ConsensusEngine
from repoman.core.events import EventBus
from repoman.core.state import JobStatus, Phase, PipelineResult, PipelineState
from repoman.execution.build_runner import ValidationEngine
from repoman.execution.file_ops import FileOps
from repoman.models.router import ModelRouter
from repoman.utils.exceptions import reraise_if_fatal

log = structlog.get_logger()


class Pipeline:
    """Orchestrates the full 7-phase repo transformation pipeline."""

    def __init__(self, config: Settings, event_bus: EventBus | None = None) -> None:
        """Initialise the pipeline with all agents and services.

        Args:
            config: Application settings.
            event_bus: Optional shared event bus (e.g., API-owned) for broadcasting.
        """
        self._config = config
        self.event_bus = event_bus or EventBus()
        self._router = ModelRouter(config)
        self._ingester = RepoIngester(config)
        self._consensus_engine = ConsensusEngine(config, self.event_bus)
        self._validator = ValidationEngine()

        self._architect = ArchitectAgent(self._router)
        self._auditor = AuditorAgent(self._router)
        self._builder = BuilderAgent(self._router)
        self._orchestrator = OrchestratorAgent(self._router)

        self._knowledge_base = None
        if config.learning_enabled:
            try:
                from repoman.learning.knowledge_base import KnowledgeBase

                self._knowledge_base = KnowledgeBase(config)
            except Exception as exc:
                log.warning("knowledge_base_disabled", error=str(exc))

    async def run(self, repo_url: str, job_id: str | None = None) -> PipelineResult:
        """Execute the full pipeline for a repository URL.

        Args:
            repo_url: Git repository URL to transform.
            job_id: Optional externally-provided job identifier.

        Returns:
            PipelineResult with all phases' outputs.
        """
        state_kwargs: dict[str, Any] = {"repo_url": repo_url, "status": JobStatus.running}
        if job_id is not None:
            state_kwargs["job_id"] = job_id
        state = PipelineState(**state_kwargs)
        start_time = time.time()

        async def emit(event: str, data: dict[str, Any] | None = None) -> None:
            payload: dict[str, Any] = {"job_id": state.job_id}
            if data:
                payload.update(data)
            await self.event_bus.emit(event, payload)

        await emit("pipeline_started", {"repo_url": repo_url})

        try:
            # Phase 1: Ingestion
            state.current_phase = Phase.ingestion
            await emit("phase_started", {"phase": Phase.ingestion.value})
            state.snapshot = await self._ingester.ingest(repo_url)
            await emit("phase_completed", {"phase": Phase.ingestion.value})

            # Phase 2: Parallel audit
            state.current_phase = Phase.audit
            await emit("phase_started", {"phase": Phase.audit.value})
            audit_tasks = [
                ("architect", self._architect.audit(state.snapshot)),
                ("auditor", self._auditor.audit(state.snapshot)),
                ("builder", self._builder.audit(state.snapshot)),
            ]
            audit_results = await asyncio.gather(
                *[t for _, t in audit_tasks],
                return_exceptions=True,
            )
            failed_audit_agents: list[str] = []
            for (agent_name, _), audit_result in zip(audit_tasks, audit_results):
                if isinstance(audit_result, BaseException):
                    failed_audit_agents.append(agent_name)
                    reraise_if_fatal(audit_result)
                    log.warning("audit_failed", agent=agent_name, error=str(audit_result))
                    continue
                state.audit_reports.append(audit_result)

            if not state.audit_reports:
                raise RuntimeError(
                    f"All audit agents failed (agents: {', '.join(failed_audit_agents)})"
                )
            await emit(
                "phase_completed",
                {"phase": Phase.audit.value, "reports": len(state.audit_reports)},
            )

            # Phase 3: Consensus
            state.current_phase = Phase.consensus
            await emit("phase_started", {"phase": Phase.consensus.value})
            state.consensus = await self._consensus_engine.run(
                state.audit_reports,
                [self._architect, self._auditor, self._builder],
                self._orchestrator,
                job_id=state.job_id,
            )
            await emit(
                "phase_completed",
                {"phase": Phase.consensus.value, "achieved": state.consensus.achieved},
            )

            # Phase 4: Execution
            state.current_phase = Phase.execution
            await emit("phase_started", {"phase": Phase.execution.value})
            file_ops = FileOps(state.snapshot.clone_path)
            change_sets = await self._builder.execute_plan(
                state.consensus.unified_plan, state.snapshot, file_ops
            )
            state.change_sets.extend(change_sets)
            await emit(
                "phase_completed",
                {"phase": Phase.execution.value, "steps": len(change_sets)},
            )

            # Phase 5: Review
            state.current_phase = Phase.review
            await emit("phase_started", {"phase": Phase.review.value})
            review_tasks = [
                ("architect", self._architect.review_changes(state.change_sets, state.snapshot)),
                ("auditor", self._auditor.review_changes(state.change_sets, state.snapshot)),
            ]
            review_results = await asyncio.gather(
                *[t for _, t in review_tasks],
                return_exceptions=True,
            )
            rejections: list[str] = []
            successful_reviews = 0
            failed_review_agents: list[str] = []
            for (agent_name, _), review in zip(review_tasks, review_results):
                if isinstance(review, BaseException):
                    failed_review_agents.append(agent_name)
                    reraise_if_fatal(review)
                    log.warning("review_failed", agent=agent_name, error=str(review))
                    continue
                successful_reviews += 1
                if isinstance(review, dict) and not review.get("approved", True):
                    rejections.extend(review.get("rejections", []))

            if successful_reviews == 0:
                raise RuntimeError(
                    f"All review agents failed (agents: {', '.join(failed_review_agents)})"
                )
            if rejections:
                fix_sets = await self._builder.apply_fixes(rejections, state.snapshot, file_ops)
                state.change_sets.extend(fix_sets)
            state.review_approved = len(rejections) == 0
            await emit(
                "phase_completed",
                {"phase": Phase.review.value, "approved": state.review_approved},
            )

            # Phase 6: Validation
            state.current_phase = Phase.validation
            await emit("phase_started", {"phase": Phase.validation.value})
            state.validation = await self._validator.validate(
                state.snapshot.clone_path, state.snapshot.primary_language
            )
            await emit(
                "phase_completed",
                {"phase": Phase.validation.value, "passed": state.validation.all_passed},
            )

            # Phase 7: Learning
            state.current_phase = Phase.learning
            if self._knowledge_base:
                await emit("phase_started", {"phase": Phase.learning.value})
                result_for_learning = self._build_result(state, start_time, JobStatus.completed)
                self._knowledge_base.learn_from_run(result_for_learning)
                await emit("phase_completed", {"phase": Phase.learning.value})

            state.status = JobStatus.completed

        except Exception as exc:
            log.error("pipeline_failed", error=str(exc), exc_info=True)
            state.status = JobStatus.failed
            state.errors.append(str(exc))
            await emit("pipeline_failed", {"error": str(exc)})

        result = self._build_result(state, start_time, state.status)
        await emit("pipeline_completed", {"status": state.status.value})
        return result

    def _build_result(
        self, state: PipelineState, start_time: float, status: JobStatus
    ) -> PipelineResult:
        """Construct a PipelineResult from the current pipeline state.

        Args:
            state: Current pipeline state.
            start_time: Unix timestamp when the pipeline started.
            status: Final job status.

        Returns:
            Fully populated PipelineResult.
        """
        before_score = state.snapshot.health_score if state.snapshot else 0.0
        after_score = state.validation.health_score if state.validation else before_score
        issues_fixed = sum(
            len(r.critical_issues) + len(r.major_issues) for r in state.audit_reports
        )

        return PipelineResult(
            job_id=state.job_id,
            status=status,
            repo_url=state.repo_url,
            before_snapshot=state.snapshot,
            audit_reports=state.audit_reports,
            consensus=state.consensus,
            change_sets=state.change_sets,
            validation=state.validation,
            before_score=before_score,
            after_score=after_score,
            issues_fixed=issues_fixed,
            total_tokens_used=state.tokens_used,
            total_duration_seconds=round(time.time() - start_time, 2),
            error=state.errors[-1] if state.errors else None,
        )
