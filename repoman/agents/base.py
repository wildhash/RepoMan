"""Abstract base agent."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

import structlog

from repoman.core.state import AgentAuditReport, AgentVote, ChangeSet, RepoSnapshot
from repoman.models.base import Message
from repoman.models.router import ModelRouter

log = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class BaseAgent(ABC):
    """Abstract agent that all concrete agents inherit from."""

    def __init__(self, name: str, role: str, router: ModelRouter) -> None:
        """Initialise the agent.

        Args:
            name: Human-readable agent name.
            role: Role key used by the model router.
            router: Model router instance.
        """
        self.name = name
        self.role = role
        self._router = router
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load the system prompt from the corresponding .md file.

        Returns:
            System prompt string.
        """
        prompt_file = _PROMPTS_DIR / f"{self.role}_system.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return f"You are the {self.name} agent. Respond carefully and precisely."

    async def _call_llm(self, user_content: str) -> str:
        """Send a single user message and return the text response.

        Args:
            user_content: User message content.

        Returns:
            Model response as a plain string.
        """
        messages = [Message(role="user", content=user_content)]
        response = await self._router.complete(self.role, messages, self._system_prompt)
        return response.content

    async def _call_llm_json(self, user_content: str) -> dict:
        """Send a single user message expecting a JSON response.

        Strips markdown code fences and parses the result.

        Args:
            user_content: User message content.

        Returns:
            Parsed JSON dictionary.
        """
        messages = [Message(role="user", content=user_content)]
        response = await self._router.complete_json(self.role, messages, self._system_prompt)
        content = response.content.strip()
        # Strip markdown fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Attempt to re-prompt once
            messages.append(Message(role="assistant", content=response.content))
            messages.append(Message(role="user", content="Your response was not valid JSON. Please return only a valid JSON object."))
            retry = await self._router.complete_json(self.role, messages, self._system_prompt)
            retry_content = retry.content.strip()
            retry_content = re.sub(r"^```(?:json)?\s*", "", retry_content)
            retry_content = re.sub(r"\s*```$", "", retry_content)
            return json.loads(retry_content)

    @abstractmethod
    async def audit(self, snapshot: RepoSnapshot) -> AgentAuditReport:
        """Perform a full audit of the repository snapshot.

        Args:
            snapshot: Repository state to audit.

        Returns:
            Detailed audit report.
        """

    @abstractmethod
    async def propose_plan(self, audit_reports: list[AgentAuditReport]) -> dict:
        """Propose an improvement plan based on audit reports.

        Args:
            audit_reports: All agents' audit reports.

        Returns:
            Plan dictionary.
        """

    @abstractmethod
    async def critique_plans(self, other_plans: dict[str, dict]) -> dict:
        """Critique other agents' proposals.

        Args:
            other_plans: Mapping of agent name to their plan.

        Returns:
            Critique dictionary.
        """

    @abstractmethod
    async def revise_plan(self, own_plan: dict, critiques: dict) -> dict:
        """Revise own plan in light of received critiques.

        Args:
            own_plan: The agent's previously proposed plan.
            critiques: Critiques from other agents.

        Returns:
            Revised plan dictionary.
        """

    @abstractmethod
    async def vote_on_plan(self, unified_plan: dict) -> AgentVote:
        """Cast a vote on the unified plan.

        Args:
            unified_plan: The orchestrator's synthesised plan.

        Returns:
            AgentVote instance.
        """

    @abstractmethod
    async def review_changes(
        self, change_sets: list[ChangeSet], snapshot: RepoSnapshot
    ) -> dict:
        """Review applied change sets and approve or reject.

        Args:
            change_sets: Changes made by the builder.
            snapshot: Current repository snapshot.

        Returns:
            Review result dictionary with 'approved' bool and 'rejections' list.
        """
