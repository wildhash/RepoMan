"""Code complexity metrics."""

from __future__ import annotations

import ast
from pathlib import Path


def cyclomatic_complexity(source: str) -> int:
    """Estimate cyclomatic complexity of a Python source string.

    Counts branching constructs (if/elif/for/while/except/with/assert).

    Args:
        source: Python source code.

    Returns:
        Complexity integer (minimum 1).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 1

    complexity = 1
    branch_types = (
        ast.If, ast.For, ast.While, ast.ExceptHandler,
        ast.With, ast.Assert, ast.comprehension,
    )
    for node in ast.walk(tree):
        if isinstance(node, branch_types):
            complexity += 1
    return complexity


def analyse_python_file(path: str) -> dict:
    """Analyse a Python file for basic complexity metrics.

    Args:
        path: Path to the Python file.

    Returns:
        Dict with keys: functions, classes, complexity, lines.
    """
    try:
        source = Path(path).read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return {"functions": 0, "classes": 0, "complexity": 0, "lines": 0}

    functions = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    return {
        "functions": functions,
        "classes": classes,
        "complexity": cyclomatic_complexity(source),
        "lines": source.count("\n") + 1,
    }
