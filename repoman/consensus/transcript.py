"""Debate transcript utilities."""

from __future__ import annotations

from repoman.core.state import DebateMessage


def format_transcript(transcript: list[DebateMessage]) -> str:
    """Format a debate transcript as a human-readable string.

    Args:
        transcript: List of debate messages.

    Returns:
        Formatted transcript string.
    """
    lines = []
    for msg in transcript:
        ts = msg.timestamp.strftime("%H:%M:%S")
        agreement = f" [{msg.agreement_level:.1f}]" if msg.agreement_level is not None else ""
        lines.append(f"[{ts}] {msg.agent} ({msg.role}){agreement}: {msg.content[:200]}")
    return "\n".join(lines)
