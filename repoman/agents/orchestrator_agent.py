"""Orchestrator agent — plan synthesis and final decision-making."""

from __future__ import annotations

import json

from repoman.agents.base import BaseAgent
from repoman.core.state import AgentAuditReport, AgentVote, ChangeSet, RepoSnapshot
from repoman.models.router import ModelRouter


class OrchestratorAgent(BaseAgent):
    """Mediator agent that synthesises plans and makes final decisions."""

    def __init__(self, router: ModelRouter) -> None:
        """Initialise the Orchestrator agent.

        Args:
            router: Model router instance.
        """
        super().__init__(name="Orchestrator", role="orchestrator", router=router)

    async def audit(self, snapshot: RepoSnapshot) -> AgentAuditReport:
        """Perform a high-level overview audit.

        Args:
            snapshot: Repository state.

        Returns:
            AgentAuditReport with an orchestration perspective.
        """
        prompt = f"""Provide a high-level overview audit of this repository.

Repository: {snapshot.url}
Language: {snapshot.primary_language}
Health score: {snapshot.health_score}

Return a JSON object with the standard audit structure."""
        data = await self._call_llm_json(prompt)
        from repoman.core.state import Issue

        def parse_issues(raw: list) -> list[Issue]:
            issues = []
            for item in raw:
                if isinstance(item, dict):
                    issues.append(Issue(
                        severity=item.get("severity", "minor"),
                        category=item.get("category", "architecture"),
                        file_path=item.get("file_path"),
                        line_number=item.get("line_number"),
                        description=item.get("description", ""),
                        suggested_fix=item.get("suggested_fix", ""),
                    ))
            return issues

        return AgentAuditReport(
            agent_name=self.name,
            agent_role=self.role,
            model_used=self._router._config.orchestrator_model,
            critical_issues=parse_issues(data.get("critical_issues", [])),
            major_issues=parse_issues(data.get("major_issues", [])),
            minor_issues=parse_issues(data.get("minor_issues", [])),
            scores=data.get("scores", {}),
            overall_score=float(data.get("overall_score", 0.0)),
            executive_summary=data.get("executive_summary", ""),
            estimated_effort=data.get("estimated_effort", ""),
        )

    async def propose_plan(self, audit_reports: list[AgentAuditReport]) -> dict:
        """Propose an orchestration-level plan.

        Args:
            audit_reports: All agents' audit reports.

        Returns:
            Plan dictionary.
        """
        prompt = f"""Propose a unified improvement plan synthesising all audit findings.

Audit reports: {len(audit_reports)} agents
Critical issues total: {sum(len(r.critical_issues) for r in audit_reports)}

Return a JSON object with keys: priority_order (list), steps (dict), rationale (str)."""
        return await self._call_llm_json(prompt)

    async def critique_plans(self, other_plans: dict[str, dict]) -> dict:
        """Critique other agents' plans as a mediator.

        Args:
            other_plans: Mapping of agent name to their plan.

        Returns:
            Critique dictionary.
        """
        prompt = f"""As mediator, critique these plans for conflicts and gaps.

Plans:
{json.dumps(other_plans, indent=2)}

Return JSON with: critiques (dict), blocking_concerns (list), minor_concerns (list)."""
        return await self._call_llm_json(prompt)

    async def revise_plan(self, own_plan: dict, critiques: dict) -> dict:
        """Revise plan based on critiques.

        Args:
            own_plan: Previously proposed plan.
            critiques: Critiques received.

        Returns:
            Revised plan dictionary.
        """
        prompt = f"""Revise the orchestration plan based on critiques.

Plan:
{json.dumps(own_plan, indent=2)}

Critiques:
{json.dumps(critiques, indent=2)}

Return your revised plan as a JSON object."""
        return await self._call_llm_json(prompt)

    async def vote_on_plan(self, unified_plan: dict) -> AgentVote:
        """Vote on the final unified plan.

        Args:
            unified_plan: The synthesised plan to evaluate.

        Returns:
            AgentVote instance.
        """
        prompt = f"""Vote on this unified plan from a holistic perspective.

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

    async def review_changes(
        self, change_sets: list[ChangeSet], snapshot: RepoSnapshot
    ) -> dict:
        """Review changes for overall coherence.

        Args:
            change_sets: Changes made by the builder.
            snapshot: Current repository snapshot.

        Returns:
            Review result with 'approved' bool and 'rejections' list.
        """
        changes_summary = "\n".join(
            f"- {cs.step_name}: {cs.summary}" for cs in change_sets
        )
        prompt = f"""Review these changes for overall coherence and completeness.

Changes:
{changes_summary}

Return JSON with: approved (bool), rejections (list of str), concerns (list of str)."""
        return await self._call_llm_json(prompt)

    async def synthesize_plans(self, plans: dict[str, dict]) -> dict:
        """Synthesise multiple agent plans into one unified plan.

        Args:
            plans: Mapping of agent name to their proposed plan.

        Returns:
            Unified plan dictionary.
        """
        prompt = f"""Synthesise these agent plans into a single unified improvement plan.

Plans:
{json.dumps(plans, indent=2)}

Prioritise: critical bugs > security > architecture > tests > docs

Return a JSON unified plan with: priority_order (list), steps (dict keyed by step name), rationale (str), estimated_improvement (float)."""
        return await self._call_llm_json(prompt)

    async def make_final_decision(
        self,
        plans: dict[str, dict],
        critiques: dict[str, dict],
        votes: dict[str, AgentVote],
    ) -> dict:
        """Make a final binding decision when consensus was not reached.

        Args:
            plans: All agent plans.
            critiques: All critiques exchanged.
            votes: All votes cast.

        Returns:
            Final unified plan dictionary.
        """
        votes_summary = {
            name: {"score": v.score, "rationale": v.rationale}
            for name, v in votes.items()
        }
        prompt = f"""Consensus was not reached. Make a final binding decision.

Plans submitted: {list(plans.keys())}
Vote scores: {json.dumps(votes_summary, indent=2)}

Return the best unified plan as a JSON object with: priority_order (list), steps (dict), rationale (str), estimated_improvement (float)."""
        return await self._call_llm_json(prompt)
