"""Git operations on the cloned repository."""

from __future__ import annotations

import asyncio

import structlog

log = structlog.get_logger()


async def git_commit(repo_path: str, message: str) -> bool:
    """Stage all changes and create a commit.

    Args:
        repo_path: Absolute path to the git repository.
        message: Commit message.

    Returns:
        True if commit succeeded, False otherwise.
    """
    try:
        add_proc = await asyncio.create_subprocess_exec(
            "git",
            "add",
            ".",
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await add_proc.communicate()

        commit_proc = await asyncio.create_subprocess_exec(
            "git",
            "commit",
            "-m",
            message,
            "--allow-empty",
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await commit_proc.communicate()
        if commit_proc.returncode != 0:
            log.warning("git_commit_failed", message=message, error=stderr.decode())
            return False
        log.info("git_committed", message=message)
        return True
    except Exception as exc:
        log.error("git_commit_error", error=str(exc))
        return False


async def git_status(repo_path: str) -> str:
    """Return the output of git status.

    Args:
        repo_path: Absolute path to the git repository.

    Returns:
        git status output string.
    """
    proc = await asyncio.create_subprocess_exec(
        "git",
        "status",
        "--short",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode()
