"""Consensus debate engine."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

from repoman.agents.base import BaseAgent
from repoman.agents.orchestrator_agent import OrchestratorAgent
from repoman.config import Settings
from repoman.core.events import EventBus
from repoman.core.state import AgentAuditReport, AgentVote, ConsensusResult, DebateMessage
from repoman.utils.exceptions import reraise_if_fatal

log = structlog.get_logger()


class ConsensusEngine:
    """Runs a structured multi-round debate to reach consensus on a unified plan."""

    def __init__(self, config: Settings, event_bus: EventBus) -> None:
        """Initialise the consensus engine.

        Args:
            config: Application settings.
            event_bus: Event bus for broadcasting debate events.
        """
        self._config = config
        self._event_bus = event_bus

    async def run(
        self,
        audit_reports: list[AgentAuditReport],
        agents: list[BaseAgent],
        orchestrator: OrchestratorAgent,
        job_id: str | None = None,
    ) -> ConsensusResult:
        """Run the full debate protocol and return a ConsensusResult.

        Args:
            audit_reports: Audit reports from all agents.
            agents: Participating debate agents (excluding orchestrator).
            orchestrator: The mediating orchestrator agent.

        Returns:
            ConsensusResult with the unified plan, votes, and transcript.
        """
        transcript: list[DebateMessage] = []

        async def emit_message(msg: DebateMessage) -> None:
            payload = msg.model_dump(mode="json")
            if job_id is not None:
                payload = {"job_id": job_id, **payload}
            await self._event_bus.emit("debate_message", payload)

        # Phase 1: All agents propose plans in parallel
        proposals = await asyncio.gather(
            *[agent.propose_plan(audit_reports) for agent in agents],
            return_exceptions=True,
        )
        plans: dict[str, dict] = {}
        for agent, proposal in zip(agents, proposals):
            if isinstance(proposal, BaseException):
                reraise_if_fatal(proposal)
                log.warning("proposal_failed", agent=agent.name, error=str(proposal))
                plans[agent.name] = {}
            else:
                plans[agent.name] = proposal
                msg = DebateMessage(
                    agent=agent.name,
                    role="PROPOSAL",
                    timestamp=datetime.utcnow(),
                    content=str(proposal),
                )
                transcript.append(msg)
                await emit_message(msg)

        unified_plan: dict = {}
        votes: dict[str, AgentVote] = {}

        for round_num in range(self._config.max_consensus_rounds):
            log.info("consensus_round", round=round_num + 1)

            # Phase 2a: Each agent critiques others' plans
            critiques_list = await asyncio.gather(
                *[
                    agent.critique_plans({k: v for k, v in plans.items() if k != agent.name})
                    for agent in agents
                ],
                return_exceptions=True,
            )
            critiques: dict[str, dict] = {}
            for agent, critique in zip(agents, critiques_list):
                if isinstance(critique, BaseException):
                    reraise_if_fatal(critique)
                    critiques[agent.name] = {}
                else:
                    critiques[agent.name] = critique
                    msg = DebateMessage(
                        agent=agent.name,
                        role="CRITIQUE",
                        timestamp=datetime.utcnow(),
                        content=str(critique),
                    )
                    transcript.append(msg)
                    await emit_message(msg)

            # Phase 2b: Each agent revises their plan
            revisions = await asyncio.gather(
                *[agent.revise_plan(plans.get(agent.name, {}), critiques) for agent in agents],
                return_exceptions=True,
            )
            for agent, revision in zip(agents, revisions):
                if isinstance(revision, BaseException):
                    reraise_if_fatal(revision)
                    continue

                plans[agent.name] = revision
                msg = DebateMessage(
                    agent=agent.name,
                    role="REVISION",
                    timestamp=datetime.utcnow(),
                    content=str(revision),
                )
                transcript.append(msg)
                await emit_message(msg)

            # Phase 2c: Orchestrator synthesises
            try:
                unified_plan = await orchestrator.synthesize_plans(plans)
            except Exception as exc:
                log.warning("synthesis_failed", error=str(exc))
                unified_plan = next(iter(plans.values()), {})

            synthesis_msg = DebateMessage(
                agent=orchestrator.name,
                role="SYNTHESIS",
                timestamp=datetime.utcnow(),
                content=str(unified_plan),
            )
            transcript.append(synthesis_msg)
            await emit_message(synthesis_msg)

            # Phase 2d: All agents vote
            vote_results = await asyncio.gather(
                *[agent.vote_on_plan(unified_plan) for agent in agents],
                return_exceptions=True,
            )
            votes = {}
            for agent, vote in zip(agents, vote_results):
                if isinstance(vote, BaseException):
                    reraise_if_fatal(vote)
                    votes[agent.name] = AgentVote(
                        agent_name=agent.name,
                        score=0.0,
                        approve=False,
                        rationale=f"Vote failed: {vote}",
                    )
                else:
                    votes[agent.name] = vote
                msg = DebateMessage(
                    agent=agent.name,
                    role="VOTE",
                    timestamp=datetime.utcnow(),
                    content=str(votes[agent.name].model_dump()),
                    agreement_level=votes[agent.name].score / 10.0,
                )
                transcript.append(msg)
                await emit_message(msg)

            # Phase 2e: Check consensus
            if all(v.score >= self._config.consensus_threshold for v in votes.values()):
                log.info("consensus_reached", round=round_num + 1)
                return ConsensusResult(
                    achieved=True,
                    rounds=round_num + 1,
                    unified_plan=unified_plan,
                    votes=votes,
                    transcript=transcript,
                )

        # No consensus — orchestrator makes final decision
        log.warning("consensus_not_reached", rounds=self._config.max_consensus_rounds)
        try:
            final_plan = await orchestrator.make_final_decision(plans, critiques, votes)
        except Exception as exc:
            log.error("final_decision_failed", error=str(exc))
            final_plan = unified_plan

        final_msg = DebateMessage(
            agent=orchestrator.name,
            role="FINAL_DECISION",
            timestamp=datetime.utcnow(),
            content=str(final_plan),
        )
        transcript.append(final_msg)
        await self._event_bus.emit("debate_message", final_msg.model_dump(mode="json"))

        return ConsensusResult(
            achieved=False,
            rounds=self._config.max_consensus_rounds,
            unified_plan=final_plan,
            votes=votes,
            transcript=transcript,
        )
