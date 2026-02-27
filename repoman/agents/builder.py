"""Builder agent — implementation, tests, docs, and CI/CD."""

from __future__ import annotations

import json

from repoman.agents.base import BaseAgent
from repoman.core.state import (
    AgentAuditReport,
    AgentVote,
    ChangeSet,
    FileChange,
    Issue,
    RepoSnapshot,
)
from repoman.execution.file_ops import FileOps
from repoman.models.router import ModelRouter


class BuilderAgent(BaseAgent):
    """Implementation-focused agent powered by Claude Sonnet."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the Builder agent.

        Args:
            router: Model router instance.
        """
        super().__init__(name="Builder", role="builder", router=router)

    async def audit(self, snapshot: RepoSnapshot) -> AgentAuditReport:
        """Audit repository for implementation quality and missing components.

        Args:
            snapshot: Repository state.

        Returns:
            AgentAuditReport with implementation findings.
        """
        prompt = f"""Audit this repository for implementation quality.

Repository: {snapshot.url}
Language: {snapshot.primary_language}
Has tests: {snapshot.has_tests}
Has README: {snapshot.has_readme}
Has CI: {snapshot.has_ci}
Has Dockerfile: {snapshot.has_dockerfile}
Total files: {snapshot.total_files}
Total lines: {snapshot.total_lines}

Return a JSON object with:
{{
  "critical_issues": [],
  "major_issues": [{{"severity": "major", "category": "docs", "file_path": null, "line_number": null, "description": "...", "suggested_fix": "..."}}],
  "minor_issues": [...],
  "architecture_changes": [],
  "new_files_needed": [{{"path": "...", "purpose": "..."}}],
  "files_to_refactor": [],
  "files_to_delete": [],
  "scores": {{"architecture": 5.0, "code_quality": 5.0, "test_coverage": 5.0, "security": 5.0, "documentation": 5.0, "performance": 5.0, "maintainability": 5.0, "deployment_readiness": 5.0}},
  "overall_score": 5.0,
  "executive_summary": "...",
  "estimated_effort": "..."
}}"""
        data = await self._call_llm_json(prompt)
        return self._parse_audit_report(data)

    def _parse_audit_report(self, data: dict) -> AgentAuditReport:
        """Convert raw LLM JSON to an AgentAuditReport.

        Args:
            data: Parsed JSON dictionary from the LLM.

        Returns:
            AgentAuditReport instance.
        """

        def parse_issues(raw: list) -> list[Issue]:
            issues = []
            for item in raw:
                if isinstance(item, dict):
                    issues.append(
                        Issue(
                            severity=item.get("severity", "minor"),
                            category=item.get("category", "docs"),
                            file_path=item.get("file_path"),
                            line_number=item.get("line_number"),
                            description=item.get("description", ""),
                            suggested_fix=item.get("suggested_fix", ""),
                        )
                    )
            return issues

        return AgentAuditReport(
            agent_name=self.name,
            agent_role=self.role,
            model_used=self._router._config.builder_model,
            critical_issues=parse_issues(data.get("critical_issues", [])),
            major_issues=parse_issues(data.get("major_issues", [])),
            minor_issues=parse_issues(data.get("minor_issues", [])),
            architecture_changes=data.get("architecture_changes", []),
            new_files_needed=data.get("new_files_needed", []),
            files_to_refactor=data.get("files_to_refactor", []),
            files_to_delete=data.get("files_to_delete", []),
            scores=data.get("scores", {}),
            overall_score=float(data.get("overall_score", 0.0)),
            executive_summary=data.get("executive_summary", ""),
            estimated_effort=data.get("estimated_effort", ""),
        )

    async def propose_plan(self, audit_reports: list[AgentAuditReport]) -> dict:
        """Propose an implementation plan.

        Args:
            audit_reports: All agents' audit reports.

        Returns:
            Plan dictionary.
        """
        new_files = [item for report in audit_reports for item in report.new_files_needed]
        prompt = f"""Propose an implementation plan: new files, tests, docs, and CI/CD setup.

New files needed across all audits:
{json.dumps(new_files, indent=2)}

Return a JSON object with keys: priority_order (list), steps (dict), rationale (str)."""
        return await self._call_llm_json(prompt)

    async def critique_plans(self, other_plans: dict[str, dict]) -> dict:
        """Critique other agents' proposals from an implementation perspective.

        Args:
            other_plans: Mapping of agent name to their plan.

        Returns:
            Critique dictionary.
        """
        prompt = f"""Critique these plans from an implementation feasibility perspective.

Plans:
{json.dumps(other_plans, indent=2)}

Return JSON with: critiques (dict), blocking_concerns (list), minor_concerns (list)."""
        return await self._call_llm_json(prompt)

    async def revise_plan(self, own_plan: dict, critiques: dict) -> dict:
        """Revise own plan based on critiques.

        Args:
            own_plan: Previously proposed plan.
            critiques: Critiques received.

        Returns:
            Revised plan dictionary.
        """
        prompt = f"""Revise your implementation plan.

Your plan:
{json.dumps(own_plan, indent=2)}

Critiques:
{json.dumps(critiques, indent=2)}

Return your revised plan as a JSON object."""
        return await self._call_llm_json(prompt)

    async def vote_on_plan(self, unified_plan: dict) -> AgentVote:
        """Vote on the unified plan from an implementation perspective.

        Args:
            unified_plan: The synthesised plan to evaluate.

        Returns:
            AgentVote instance.
        """
        prompt = f"""Vote on this unified plan from an implementation perspective.

Plan:
{json.dumps(unified_plan, indent=2)}

Return JSON with: agent_name (str), score (float 0-10), approve (bool), blocking_concerns (list), minor_concerns (list), rationale (str)."""
        data = await self._call_llm_json(prompt)
        score = float(data.get("score", 5.0))
        return AgentVote(
            agent_name=self.name,
            score=score,
            approve=data.get("approve", score >= 7.0),
            blocking_concerns=data.get("blocking_concerns", []),
            minor_concerns=data.get("minor_concerns", []),
            rationale=data.get("rationale", ""),
        )

    async def review_changes(self, change_sets: list[ChangeSet], snapshot: RepoSnapshot) -> dict:
        """Review applied changes for implementation quality.

        Args:
            change_sets: Changes made by the builder.
            snapshot: Current repository snapshot.

        Returns:
            Review result with 'approved' bool and 'rejections' list.
        """
        changes_summary = "\n".join(f"- {cs.step_name}: {cs.summary}" for cs in change_sets)
        prompt = f"""Review these changes for implementation quality and completeness.

Changes:
{changes_summary}

Return JSON with: approved (bool), rejections (list of str), concerns (list of str)."""
        return await self._call_llm_json(prompt)

    async def execute_plan(
        self,
        unified_plan: dict,
        snapshot: RepoSnapshot,
        file_ops: FileOps,
    ) -> list[ChangeSet]:
        """Execute the unified plan step by step.

        Args:
            unified_plan: The orchestrator's approved plan.
            snapshot: Current repository snapshot.
            file_ops: File operations interface.

        Returns:
            List of ChangeSets describing every change made.
        """
        from repoman.constants import EXECUTION_ORDER

        change_sets: list[ChangeSet] = []
        steps = unified_plan.get("steps", {})

        for step_name in EXECUTION_ORDER:
            if step_name not in steps:
                continue
            step = steps[step_name]
            prompt = f"""Execute this step: {step_name}

Step description: {step.get("description", "")}
Files to modify: {json.dumps(step.get("files", []))}
Changes to make: {json.dumps(step.get("changes", []))}

Repository: {snapshot.url} ({snapshot.primary_language})

Return a JSON ChangeSet:
{{
  "step_name": "{step_name}",
  "files_created": [{{"path": "...", "action": "create", "content": "...", "summary": "..."}}],
  "files_modified": [{{"path": "...", "action": "modify", "content": "...", "summary": "..."}}],
  "files_deleted": [],
  "summary": "..."
}}"""
            try:
                data = await self._call_llm_json(prompt)
                cs = ChangeSet(
                    step_name=step_name,
                    files_created=[FileChange(**f) for f in data.get("files_created", [])],
                    files_modified=[FileChange(**f) for f in data.get("files_modified", [])],
                    files_deleted=data.get("files_deleted", []),
                    summary=data.get("summary", f"Completed {step_name}"),
                )
                # Apply changes
                for fc in cs.files_created:
                    if fc.content:
                        await file_ops.create_file(fc.path, fc.content)
                for fc in cs.files_modified:
                    if fc.content:
                        await file_ops.modify_file(fc.path, fc.content)
                for path in cs.files_deleted:
                    await file_ops.delete_file(path)
                change_sets.append(cs)
            except Exception as exc:
                change_sets.append(
                    ChangeSet(
                        step_name=step_name,
                        summary=f"Step failed: {exc}",
                    )
                )

        return change_sets

    async def apply_fixes(
        self,
        rejections: list[str],
        snapshot: RepoSnapshot,
        file_ops: FileOps,
    ) -> list[ChangeSet]:
        """Apply fixes for rejected changes.

        Args:
            rejections: List of rejection reasons.
            snapshot: Current repository snapshot.
            file_ops: File operations interface.

        Returns:
            List of fix ChangeSets.
        """
        prompt = f"""Apply fixes for these review rejections:

{json.dumps(rejections, indent=2)}

Repository: {snapshot.url} ({snapshot.primary_language})

Return a JSON ChangeSet with fixes applied."""
        try:
            data = await self._call_llm_json(prompt)
            cs = ChangeSet(
                step_name="apply_fixes",
                files_created=[FileChange(**f) for f in data.get("files_created", [])],
                files_modified=[FileChange(**f) for f in data.get("files_modified", [])],
                files_deleted=data.get("files_deleted", []),
                summary=data.get("summary", "Applied reviewer fixes"),
            )
            for fc in cs.files_created:
                if fc.content:
                    await file_ops.create_file(fc.path, fc.content)
            for fc in cs.files_modified:
                if fc.content:
                    await file_ops.modify_file(fc.path, fc.content)
            return [cs]
        except Exception as exc:
            return [ChangeSet(step_name="apply_fixes", summary=f"Fix failed: {exc}")]
