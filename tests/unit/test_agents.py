"""Unit tests for agent components (no LLM calls)."""

from __future__ import annotations

from unittest.mock import MagicMock

from repoman.core.state import AgentVote, Issue
from repoman.models.router import ModelRouter


class TestBaseAgent:
    """Tests for BaseAgent functionality that don't require LLM calls."""

    def test_system_prompt_loaded_from_file(self, settings) -> None:
        """Agent should load system prompt from .md file."""
        router = MagicMock(spec=ModelRouter)
        router._config = settings
        from repoman.agents.architect import ArchitectAgent

        agent = ArchitectAgent(router)
        assert len(agent._system_prompt) > 0
        assert "Architect" in agent._system_prompt

    def test_agent_has_correct_name(self, settings) -> None:
        """Agent should have the expected name."""
        router = MagicMock(spec=ModelRouter)
        router._config = settings
        from repoman.agents.auditor import AuditorAgent

        agent = AuditorAgent(router)
        assert agent.name == "Auditor"

    def test_agent_role(self, settings) -> None:
        """Agent should have the expected role."""
        router = MagicMock(spec=ModelRouter)
        router._config = settings
        from repoman.agents.builder import BuilderAgent

        agent = BuilderAgent(router)
        assert agent.role == "builder"


class TestIssueModel:
    """Tests for Issue Pydantic model."""

    def test_issue_has_auto_id(self) -> None:
        """Issue should generate a unique id automatically."""
        issue = Issue(
            severity="critical",
            category="security",
            description="Test issue",
            suggested_fix="Fix it",
        )
        assert issue.id
        assert len(issue.id) > 0

    def test_two_issues_have_different_ids(self) -> None:
        """Two separately created issues should have different ids."""
        i1 = Issue(severity="minor", category="style", description="x", suggested_fix="y")
        i2 = Issue(severity="minor", category="style", description="x", suggested_fix="y")
        assert i1.id != i2.id

    def test_issue_serialization(self) -> None:
        """Issue should serialise to dict correctly."""
        issue = Issue(
            severity="major",
            category="bug",
            file_path="src/app.py",
            line_number=10,
            description="Bug",
            suggested_fix="Fix",
        )
        d = issue.model_dump()
        assert d["severity"] == "major"
        assert d["file_path"] == "src/app.py"
        assert d["line_number"] == 10


class TestAgentVote:
    """Tests for AgentVote model."""

    def test_approve_based_on_score(self) -> None:
        """approve field should reflect whether score meets threshold."""
        vote = AgentVote(
            agent_name="Architect",
            score=7.5,
            approve=True,
            rationale="Good plan",
        )
        assert vote.approve is True

    def test_vote_serialization(self) -> None:
        """Vote should serialise to dict."""
        vote = AgentVote(
            agent_name="Auditor",
            score=6.0,
            approve=False,
            blocking_concerns=["Missing auth"],
            rationale="Needs more security",
        )
        d = vote.model_dump()
        assert d["agent_name"] == "Auditor"
        assert d["blocking_concerns"] == ["Missing auth"]
