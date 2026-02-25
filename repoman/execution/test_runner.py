"""Language-specific test runner."""

from __future__ import annotations

import asyncio

import structlog

from repoman.core.state import ValidationResult

log = structlog.get_logger()


async def run_command(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run a subprocess command.

    Args:
        cmd: Command and arguments.
        cwd: Working directory.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode(), stderr.decode()
    except TimeoutError:
        return 1, "", "Timed out"
    except FileNotFoundError as exc:
        return 1, "", f"Command not found: {exc}"


async def run_tests(repo_path: str, language: str) -> ValidationResult:
    """Run language-specific tests.

    Args:
        repo_path: Absolute path to the repository.
        language: Primary programming language.

    Returns:
        ValidationResult for the test run.
    """
    lang = language.lower()
    if lang == "python":
        rc, stdout, stderr = await run_command(["python", "-m", "pytest", "--tb=short", "-q"], repo_path)
    elif lang in ("javascript", "typescript"):
        rc, stdout, stderr = await run_command(["npm", "test", "--", "--watchAll=false"], repo_path)
    elif lang == "rust":
        rc, stdout, stderr = await run_command(["cargo", "test"], repo_path)
    elif lang == "go":
        rc, stdout, stderr = await run_command(["go", "test", "./..."], repo_path)
    else:
        return ValidationResult(check_name="tests", passed=True, output="No test runner for language", details={})

    output = stdout + stderr
    return ValidationResult(
        check_name="tests",
        passed=rc == 0,
        output=output[:2000],
        details={"returncode": rc},
    )
