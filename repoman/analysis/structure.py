"""File tree analysis utilities."""

from __future__ import annotations

from pathlib import Path

from repoman.constants import SKIP_DIRS


def build_file_tree(root_path: str) -> list[str]:
    """Walk a directory and return relative paths of all non-ignored files.

    Args:
        root_path: Root directory to walk.

    Returns:
        Sorted list of relative file paths.
    """
    import os

    files: list[str] = []
    root = Path(root_path)
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            files.append(str(fpath.relative_to(root)))
    return sorted(files)


def get_directory_structure(file_tree: list[str]) -> dict:
    """Build a nested dict representing the directory structure.

    Args:
        file_tree: List of relative file paths.

    Returns:
        Nested dict where keys are directory/file names.
    """
    tree: dict = {}
    for path in file_tree:
        parts = path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None
    return tree
