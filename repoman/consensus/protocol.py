"""Consensus protocol message types and rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProtocolRules:
    """Rules governing the debate protocol."""

    max_rounds: int = 5
    consensus_threshold: float = 7.0
    require_unanimous: bool = False
    allow_abstain: bool = False


VALID_ROLES = frozenset(["PROPOSAL", "CRITIQUE", "REVISION", "VOTE", "SYNTHESIS", "FINAL_DECISION"])
