"""Vote aggregation utilities."""

from __future__ import annotations

from repoman.core.state import AgentVote


def aggregate_votes(votes: dict[str, AgentVote]) -> dict:
    """Aggregate individual votes into a summary.

    Args:
        votes: Mapping of agent name to their vote.

    Returns:
        Summary dict with average_score, approve_count, total, consensus_reached.
    """
    if not votes:
        return {"average_score": 0.0, "approve_count": 0, "total": 0, "consensus_reached": False}

    scores = [v.score for v in votes.values()]
    avg = sum(scores) / len(scores)
    approve_count = sum(1 for v in votes.values() if v.approve)

    return {
        "average_score": round(avg, 2),
        "approve_count": approve_count,
        "total": len(votes),
        "consensus_reached": all(v.approve for v in votes.values()),
        "min_score": min(scores),
        "max_score": max(scores),
    }
