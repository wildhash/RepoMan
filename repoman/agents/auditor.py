"""Auditor agent — security and quality evaluation."""

from __future__ import annotations

import json

from repoman.agents.base import BaseAgent
from repoman.core.state import AgentAuditReport, AgentVote, ChangeSet, Issue, RepoSnapshot
from repoman.models.router import ModelRouter


class AuditorAgent(BaseAgent):
    """Security and quality agent powered by GPT-4o."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the Auditor agent.

        Args:
            router: Model router instance.
        """
        super().__init__(name="Auditor", role="auditor", router=router)

    async def audit(self, snapshot: RepoSnapshot) -> AgentAuditReport:
        """Audit repository for bugs, security issues, and code quality problems.

        Args:
            snapshot: Repository state.

        Returns:
            AgentAuditReport with security and quality findings.
        """
        files_preview = "\n".join(
            f"{path}: {summary}" for path, summary in list(snapshot.file_summaries.items())[:30]
        )
        prompt = f"""Perform an adversarial security and quality audit of this repository.

Repository: {snapshot.url}
Language: {snapshot.primary_language}
Frameworks: {", ".join(snapshot.frameworks)}
Dependencies: {json.dumps(snapshot.dependencies[:20], indent=2)}

File summaries:
{files_preview}

Find every bug, security vulnerability, performance issue, and code smell.

Return a JSON object with exactly this structure:
{{
  "critical_issues": [{{"severity": "critical", "category": "security", "file_path": "...", "line_number": null, "description": "...", "suggested_fix": "..."}}],
  "major_issues": [...],
  "minor_issues": [...],
  "architecture_changes": [],
  "new_files_needed": [],
  "files_to_refactor": [{{"path": "...", "reason": "..."}}],
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
                            category=item.get("category", "bug"),
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
            model_used=self._router._config.auditor_model,
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
        """Propose a security and quality improvement plan.

        Args:
            audit_reports: All agents' audit reports.

        Returns:
            Plan dictionary.
        """
        all_critical = [
            issue.model_dump() for report in audit_reports for issue in report.critical_issues
        ]
        prompt = f"""Propose a security and quality improvement plan based on these critical issues.

Critical issues:
{json.dumps(all_critical, indent=2, default=str)}

Return a JSON object with keys: priority_order (list), steps (dict), rationale (str)."""
        return await self._call_llm_json(prompt)

    async def critique_plans(self, other_plans: dict[str, dict]) -> dict:
        """Critique other agents' proposals from a security perspective.

        Args:
            other_plans: Mapping of agent name to their plan.

        Returns:
            Critique dictionary.
        """
        prompt = f"""Critique these plans from a security and quality perspective. Find gaps and risks.

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
        prompt = f"""Revise your security plan based on critiques.

Your plan:
{json.dumps(own_plan, indent=2)}

Critiques:
{json.dumps(critiques, indent=2)}

Return your revised plan as a JSON object."""
        return await self._call_llm_json(prompt)

    async def vote_on_plan(self, unified_plan: dict) -> AgentVote:
        """Vote on the unified plan from a security perspective.

        Args:
            unified_plan: The synthesised plan to evaluate.

        Returns:
            AgentVote instance.
        """
        prompt = f"""Vote on this unified plan from a security and quality perspective.

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
        """Review applied changes for security regressions.

        Args:
            change_sets: Changes made by the builder.
            snapshot: Current repository snapshot.

        Returns:
            Review result with 'approved' bool and 'rejections' list.
        """
        changes_summary = "\n".join(f"- {cs.step_name}: {cs.summary}" for cs in change_sets)
        prompt = f"""Review these code changes for security regressions or new vulnerabilities.

Changes:
{changes_summary}

Return JSON with: approved (bool), rejections (list of str), concerns (list of str)."""
        return await self._call_llm_json(prompt)
