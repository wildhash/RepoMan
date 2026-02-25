"""Language and framework detection."""

from __future__ import annotations

import os
from pathlib import Path

from repoman.constants import EXTENSION_TO_LANGUAGE, SKIP_DIRS


def detect_languages(clone_path: str, max_file_size_kb: int = 500) -> dict[str, float]:
    """Detect programming languages by extension weighted by line count.

    Args:
        clone_path: Root of the cloned repository.
        max_file_size_kb: Skip files larger than this.

    Returns:
        Dict mapping language name to fraction of total lines (0.0–1.0).
    """
    counts: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(clone_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            lang = EXTENSION_TO_LANGUAGE.get(ext)
            if not lang:
                continue
            fpath = Path(dirpath) / fname
            try:
                size_kb = fpath.stat().st_size / 1024
                if size_kb > max_file_size_kb:
                    continue
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                lines = text.count("\n") + 1
                counts[lang] = counts.get(lang, 0) + lines
            except (OSError, PermissionError):
                continue

    total = sum(counts.values()) or 1
    return {lang: round(count / total, 4) for lang, count in sorted(counts.items(), key=lambda x: -x[1])}


def detect_frameworks(clone_path: str) -> list[str]:
    """Detect frameworks from package manifest files.

    Args:
        clone_path: Root of the cloned repository.

    Returns:
        List of detected framework names.
    """
    frameworks: list[str] = []
    root = Path(clone_path)

    # Python
    req_file = root / "requirements.txt"
    if req_file.exists():
        text = req_file.read_text(encoding="utf-8", errors="ignore").lower()
        if "django" in text:
            frameworks.append("Django")
        if "flask" in text:
            frameworks.append("Flask")
        if "fastapi" in text:
            frameworks.append("FastAPI")
        if "tornado" in text:
            frameworks.append("Tornado")

    # JavaScript / TypeScript
    pkg_file = root / "package.json"
    if pkg_file.exists():
        text = pkg_file.read_text(encoding="utf-8", errors="ignore").lower()
        if '"react"' in text:
            frameworks.append("React")
        if '"vue"' in text:
            frameworks.append("Vue")
        if '"express"' in text:
            frameworks.append("Express")
        if '"next"' in text:
            frameworks.append("Next.js")
        if '"svelte"' in text:
            frameworks.append("Svelte")

    # Rust
    cargo_file = root / "Cargo.toml"
    if cargo_file.exists():
        text = cargo_file.read_text(encoding="utf-8", errors="ignore").lower()
        if "actix" in text:
            frameworks.append("Actix")
        if "rocket" in text:
            frameworks.append("Rocket")
        if "axum" in text:
            frameworks.append("Axum")

    # Go
    go_mod = root / "go.mod"
    if go_mod.exists():
        text = go_mod.read_text(encoding="utf-8", errors="ignore").lower()
        if "gin-gonic" in text or "gin" in text:
            frameworks.append("Gin")
        if "echo" in text:
            frameworks.append("Echo")
        if "fiber" in text:
            frameworks.append("Fiber")

    return list(dict.fromkeys(frameworks))  # deduplicate preserving order
