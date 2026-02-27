"""Dependency parsing for multiple package managers."""

from __future__ import annotations

import json
import re
from pathlib import Path


def parse_dependencies(clone_path: str) -> list[dict]:
    """Parse dependencies from manifest files.

    Args:
        clone_path: Root of the cloned repository.

    Returns:
        List of dicts with keys: name, version, type (runtime|dev).
    """
    deps: list[dict] = []
    root = Path(clone_path)

    # Python — requirements.txt
    for req_file in (root / "requirements.txt", root / "requirements-dev.txt"):
        if req_file.exists():
            dep_type = "dev" if "dev" in req_file.name else "runtime"
            for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"([A-Za-z0-9_\-\.]+)([><=!~^]+.*)?", line)
                if match:
                    deps.append(
                        {
                            "name": match.group(1),
                            "version": (match.group(2) or "").strip(),
                            "type": dep_type,
                        }
                    )

    # JavaScript — package.json
    pkg_file = root / "package.json"
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
            for name, ver in pkg.get("dependencies", {}).items():
                deps.append({"name": name, "version": ver, "type": "runtime"})
            for name, ver in pkg.get("devDependencies", {}).items():
                deps.append({"name": name, "version": ver, "type": "dev"})
        except json.JSONDecodeError:
            pass

    # Rust — Cargo.toml (simple parsing)
    cargo_file = root / "Cargo.toml"
    if cargo_file.exists():
        text = cargo_file.read_text(encoding="utf-8", errors="ignore")
        in_deps = False
        for line in text.splitlines():
            if "[dependencies]" in line:
                in_deps = True
                continue
            if in_deps and line.startswith("["):
                in_deps = False
            if in_deps:
                match = re.match(r'(\S+)\s*=\s*"([^"]+)"', line)
                if match:
                    deps.append(
                        {"name": match.group(1), "version": match.group(2), "type": "runtime"}
                    )

    # Go — go.mod
    go_mod = root / "go.mod"
    if go_mod.exists():
        for line in go_mod.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = re.match(r"\s+([^\s]+)\s+v([^\s]+)", line)
            if match:
                deps.append(
                    {"name": match.group(1), "version": f"v{match.group(2)}", "type": "runtime"}
                )

    return deps
