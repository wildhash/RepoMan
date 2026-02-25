"""Unified diff generation utilities."""

from __future__ import annotations

import difflib


def unified_diff(old: str, new: str, filename: str = "") -> str:
    """Generate a unified diff between two strings.

    Args:
        old: Original content.
        new: New content.
        filename: Optional filename label.

    Returns:
        Unified diff string.
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    label = filename or "file"
    return "".join(
        difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{label}", tofile=f"b/{label}")
    )
