"""Architect agent — system design and structure evaluation."""

from __future__ import annotations

import json

from repoman.agents.base import BaseAgent
from repoman.core.state import AgentAuditReport, AgentVote, ChangeSet, Issue, RepoSnapshot
from repoman.models.router import ModelRouter


class ArchitectAgent(BaseAgent):
    """Architecture-focused agent powered by Claude."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the Architect agent.

        Args:
            router: Model router instance.
        """
        super().__init__(name="Architect", role="architect", router=router)

    async def audit(self, snapshot: RepoSnapshot) -> AgentAuditReport:
        """Audit repository architecture and structure.

        Args:
            snapshot: Repository state.

        Returns:
            AgentAuditReport with architectural findings.
        """
        prompt = f"""Audit this repository for architectural quality.

Repository: {snapshot.url}
Primary language: {snapshot.primary_language}
Frameworks: {", ".join(snapshot.frameworks)}
Files: {len(snapshot.file_tree)}
Has README: {snapshot.has_readme}
Has tests: {snapshot.has_tests}
Has CI: {snapshot.has_ci}
Has Dockerfile: {snapshot.has_dockerfile}

File tree (first 50):
{chr(10).join(snapshot.file_tree[:50])}

Return a JSON object with exactly this structure:
{{
  "critical_issues": [{{"severity": "critical", "category": "architecture", "file_path": null, "line_number": null, "description": "...", "suggested_fix": "..."}}],
  "major_issues": [...],
  "minor_issues": [...],
  "architecture_changes": [{{"change": "...", "rationale": "..."}}],
  "new_files_needed": [{{"path": "...", "purpose": "..."}}],
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
                            category=item.get("category", "architecture"),
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
            model_used=self._router._config.architect_model,
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
        """Propose an architectural improvement plan.

        Args:
            audit_reports: All agents' audit reports.

        Returns:
            Plan dictionary.
        """
        summaries = "\n".join(f"- {r.agent_name}: {r.executive_summary}" for r in audit_reports)
        prompt = f"""Based on these audit findings, propose an architectural improvement plan.

Audit summaries:
{summaries}

Return a JSON object describing your proposed plan with keys: priority_order (list), steps (dict), rationale (str)."""
        return await self._call_llm_json(prompt)

    async def critique_plans(self, other_plans: dict[str, dict]) -> dict:
        """Critique other agents' proposals from an architectural perspective.

        Args:
            other_plans: Mapping of agent name to their plan.

        Returns:
            Critique dictionary.
        """
        plans_text = json.dumps(other_plans, indent=2)
        prompt = f"""Critique these proposed plans from an architectural perspective.

Plans:
{plans_text}

Return a JSON object with keys: critiques (dict mapping agent_name to critique str), blocking_concerns (list), minor_concerns (list)."""
        return await self._call_llm_json(prompt)

    async def revise_plan(self, own_plan: dict, critiques: dict) -> dict:
        """Revise own plan based on critiques.

        Args:
            own_plan: Previously proposed plan.
            critiques: Critiques received from other agents.

        Returns:
            Revised plan dictionary.
        """
        prompt = f"""Revise your plan based on the critiques received.

Your plan:
{json.dumps(own_plan, indent=2)}

Critiques:
{json.dumps(critiques, indent=2)}

Return your revised plan as a JSON object."""
        return await self._call_llm_json(prompt)

    async def vote_on_plan(self, unified_plan: dict) -> AgentVote:
        """Vote on the orchestrator's unified plan.

        Args:
            unified_plan: The synthesised plan to evaluate.

        Returns:
            AgentVote instance.
        """
        prompt = f"""Vote on this unified improvement plan from an architectural perspective.

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
        """Review applied changes from an architectural perspective.

        Args:
            change_sets: Changes made by the builder.
            snapshot: Current repository snapshot.

        Returns:
            Review result with 'approved' bool and 'rejections' list.
        """
        changes_summary = "\n".join(f"- {cs.step_name}: {cs.summary}" for cs in change_sets)
        prompt = f"""Review these changes applied to the repository.

Changes:
{changes_summary}

Repository: {snapshot.url} ({snapshot.primary_language})

Return JSON with: approved (bool), rejections (list of str), concerns (list of str)."""
        return await self._call_llm_json(prompt)
