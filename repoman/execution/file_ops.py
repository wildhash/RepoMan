"""Async file operations on the cloned repository."""

from __future__ import annotations

from pathlib import Path

import aiofiles  # type: ignore[import-untyped]
import structlog

log = structlog.get_logger()


class FileOps:
    """Async CRUD operations relative to a repository root."""

    def __init__(self, repo_root: str) -> None:
        """Initialise with the repository root path.

        Args:
            repo_root: Absolute path to the repository root.
        """
        self._root = Path(repo_root)

    def _resolve(self, relative_path: str) -> Path:
        """Resolve a relative path against the repo root.

        Args:
            relative_path: Path relative to repo root.

        Returns:
            Absolute Path object.
        """
        return self._root / relative_path

    async def create_file(self, path: str, content: str) -> None:
        """Create a new file, creating parent directories as needed.

        Args:
            path: Relative path within the repository.
            content: File content to write.
        """
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target, "w", encoding="utf-8") as f:
            await f.write(content)
        log.info("file_created", path=path)

    async def modify_file(self, path: str, content: str) -> None:
        """Overwrite an existing file with new content.

        Args:
            path: Relative path within the repository.
            content: New file content.
        """
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target, "w", encoding="utf-8") as f:
            await f.write(content)
        log.info("file_modified", path=path)

    async def delete_file(self, path: str) -> None:
        """Delete a file if it exists.

        Args:
            path: Relative path within the repository.
        """
        target = self._resolve(path)
        if target.exists():
            target.unlink()
            log.info("file_deleted", path=path)

    async def read_file(self, path: str) -> str:
        """Read and return a file's content.

        Args:
            path: Relative path within the repository.

        Returns:
            File content as string.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        target = self._resolve(path)
        async with aiofiles.open(target, encoding="utf-8", errors="ignore") as f:
            return await f.read()

    def list_files(self, sub_path: str = "") -> list[str]:
        """List files under an optional sub-path.

        Args:
            sub_path: Relative sub-directory to list (default: repo root).

        Returns:
            Sorted list of relative file paths.
        """
        base = self._resolve(sub_path) if sub_path else self._root
        result = []
        for fpath in base.rglob("*"):
            if fpath.is_file():
                result.append(str(fpath.relative_to(self._root)))
        return sorted(result)
