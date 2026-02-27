"""Docker sandbox execution wrapper."""

from __future__ import annotations

import asyncio

import structlog

log = structlog.get_logger()


class Sandbox:
    """Runs commands inside a Docker container for safe execution."""

    def __init__(self, image: str = "python:3.12-slim", enabled: bool = True) -> None:
        """Initialise the sandbox.

        Args:
            image: Docker image to use.
            enabled: Whether sandboxing is active.
        """
        self._image = image
        self._enabled = enabled

    async def run(
        self, command: list[str], repo_path: str, timeout: int = 120
    ) -> tuple[int, str, str]:
        """Run a command, optionally in a Docker container.

        Args:
            command: Command and arguments.
            repo_path: Path to mount as /workspace.
            timeout: Maximum execution time in seconds.

        Returns:
            Tuple of (returncode, stdout, stderr).
        """
        if self._enabled:
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "-v",
                f"{repo_path}:/workspace",
                "-w",
                "/workspace",
                self._image,
            ] + command
            cmd = docker_cmd
        else:
            cmd = command

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode or 0, stdout.decode(), stderr.decode()
        except TimeoutError:
            return 1, "", "Execution timed out"
        except Exception as exc:
            return 1, "", str(exc)
