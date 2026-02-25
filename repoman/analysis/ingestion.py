"""Repository ingestion — clone and analyse a remote repository."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import structlog

from repoman.analysis.dependency import parse_dependencies
from repoman.analysis.health import compute_initial_health_score
from repoman.analysis.language import detect_frameworks, detect_languages
from repoman.config import Settings
from repoman.constants import SKIP_DIRS
from repoman.core.state import RepoSnapshot

log = structlog.get_logger()


class RepoIngester:
    """Clones and analyses a remote git repository."""

    def __init__(self, config: Settings) -> None:
        """Initialise the ingester.

        Args:
            config: Application settings.
        """
        self._config = config

    async def ingest(self, repo_url: str) -> RepoSnapshot:
        """Clone the repository and build a RepoSnapshot.

        Args:
            repo_url: Git repository URL.

        Returns:
            Complete RepoSnapshot of the cloned repo.
        """
        tmp_dir = tempfile.mkdtemp(prefix="repoman_")
        clone_path = os.path.join(tmp_dir, "repo")

        log.info("cloning_repo", url=repo_url, path=clone_path)
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", repo_url, clone_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        return await self._analyse(repo_url, clone_path)

    async def _analyse(self, repo_url: str, clone_path: str) -> RepoSnapshot:
        """Analyse the cloned repository.

        Args:
            repo_url: Original repository URL.
            clone_path: Local path to the cloned repo.

        Returns:
            Populated RepoSnapshot.
        """
        repo_root = Path(clone_path)
        name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        # Walk file tree
        file_tree: list[str] = []
        total_lines = 0
        file_summaries: dict[str, str] = {}

        for root, dirs, files in os.walk(clone_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(repo_root))
                file_tree.append(rel)

                # Count lines for supported text files
                try:
                    size_kb = fpath.stat().st_size / 1024
                    if size_kb <= self._config.max_file_size_kb:
                        text = fpath.read_text(encoding="utf-8", errors="ignore")
                        lines = text.count("\n")
                        total_lines += lines
                        file_summaries[rel] = f"{lines} lines"
                except (OSError, PermissionError):
                    pass

                if len(file_tree) >= self._config.max_files_to_process:
                    break

        languages = detect_languages(clone_path, self._config.max_file_size_kb)
        frameworks = detect_frameworks(clone_path)
        dependencies = parse_dependencies(clone_path)
        entry_points = _find_entry_points(clone_path, languages)

        # Check existence of key files
        has_readme = any(f.lower().startswith("readme") for f in file_tree)
        has_tests = any("test" in f.lower() for f in file_tree)
        has_ci = any(".github/workflows" in f or ".circleci" in f or "Jenkinsfile" in f for f in file_tree)
        has_dockerfile = any(f.lower() == "dockerfile" or "dockerfile" in f.lower() for f in file_tree)
        has_license = any(f.lower().startswith("license") for f in file_tree)
        has_env_example = any(".env.example" in f or ".env.sample" in f for f in file_tree)

        primary_language = max(languages, key=languages.get, default="")

        snapshot = RepoSnapshot(
            url=repo_url,
            name=name,
            clone_path=clone_path,
            primary_language=primary_language,
            languages=languages,
            frameworks=frameworks,
            dependencies=dependencies,
            file_tree=file_tree,
            entry_points=entry_points,
            has_readme=has_readme,
            has_tests=has_tests,
            has_ci=has_ci,
            has_dockerfile=has_dockerfile,
            has_license=has_license,
            has_env_example=has_env_example,
            total_files=len(file_tree),
            total_lines=total_lines,
            file_summaries=file_summaries,
        )
        snapshot.health_score = compute_initial_health_score(snapshot)
        return snapshot


def _find_entry_points(clone_path: str, languages: dict[str, float]) -> list[str]:
    """Identify likely entry point files.

    Args:
        clone_path: Root of the cloned repo.
        languages: Detected language distribution.

    Returns:
        List of relative paths to entry point files.
    """
    candidates = [
        "main.py", "app.py", "server.py", "manage.py",
        "index.js", "index.ts", "server.js", "app.js",
        "src/main.rs", "src/lib.rs",
        "main.go", "cmd/main.go",
        "Main.java", "src/main/java/Main.java",
        "index.php", "main.rb",
    ]
    found = []
    root = Path(clone_path)
    for candidate in candidates:
        if (root / candidate).exists():
            found.append(candidate)
    return found
