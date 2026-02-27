"""Unit tests for consensus components."""

from __future__ import annotations

import pytest

from repoman.consensus.transcript import format_transcript
from repoman.consensus.voting import aggregate_votes
from repoman.core.state import AgentVote, DebateMessage


class TestVoteAggregation:
    """Tests for vote aggregation."""

    def test_empty_votes(self) -> None:
        """Should handle empty vote dict gracefully."""
        result = aggregate_votes({})
        assert result["average_score"] == 0.0
        assert result["total"] == 0

    def test_all_approve(self) -> None:
        """All high scores should indicate consensus reached."""
        votes = {
            "Architect": AgentVote(
                agent_name="Architect", score=8.0, approve=True, rationale="Good"
            ),
            "Auditor": AgentVote(agent_name="Auditor", score=9.0, approve=True, rationale="Secure"),
        }
        result = aggregate_votes(votes)
        assert result["consensus_reached"] is True
        assert result["approve_count"] == 2
        assert result["average_score"] == pytest.approx(8.5)

    def test_partial_consensus(self) -> None:
        """Mixed votes should not indicate consensus."""
        votes = {
            "Architect": AgentVote(agent_name="Architect", score=8.0, approve=True, rationale=""),
            "Auditor": AgentVote(agent_name="Auditor", score=5.0, approve=False, rationale=""),
        }
        result = aggregate_votes(votes)
        assert result["consensus_reached"] is False

    def test_min_max_scores(self) -> None:
        """Should compute min and max scores correctly."""
        votes = {
            "A": AgentVote(agent_name="A", score=3.0, approve=False, rationale=""),
            "B": AgentVote(agent_name="B", score=9.0, approve=True, rationale=""),
        }
        result = aggregate_votes(votes)
        assert result["min_score"] == 3.0
        assert result["max_score"] == 9.0


class TestTranscript:
    """Tests for debate transcript formatting."""

    def test_format_empty_transcript(self) -> None:
        """Empty transcript should return empty string."""
        assert format_transcript([]) == ""

    def test_format_transcript_contains_agent_name(self) -> None:
        """Formatted transcript should include agent names."""
        msg = DebateMessage(
            agent="Architect",
            role="PROPOSAL",
            content="I propose restructuring the codebase.",
        )
        result = format_transcript([msg])
        assert "Architect" in result
        assert "PROPOSAL" in result

    def test_format_with_agreement_level(self) -> None:
        """Agreement level should appear in formatted output."""
        msg = DebateMessage(
            agent="Auditor",
            role="VOTE",
            content="I agree.",
            agreement_level=0.9,
        )
        result = format_transcript([msg])
        assert "0.9" in result
