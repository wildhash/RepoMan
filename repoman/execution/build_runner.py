"""Build verification and validation engine."""

from __future__ import annotations

import structlog

from repoman.core.state import ValidationReport, ValidationResult
from repoman.execution.test_runner import run_command

log = structlog.get_logger()

_VALIDATION_MAP: dict[str, list[tuple[str, list[str]]]] = {
    "python": [
        ("lint_ruff", ["python", "-m", "ruff", "check", "."]),
        ("type_check_mypy", ["python", "-m", "mypy", ".", "--ignore-missing-imports"]),
        ("security_bandit", ["python", "-m", "bandit", "-r", ".", "-q"]),
    ],
    "javascript": [
        ("lint_eslint", ["npx", "eslint", ".", "--max-warnings=0"]),
        ("security_audit", ["npm", "audit", "--audit-level=high"]),
    ],
    "typescript": [
        ("lint_eslint", ["npx", "eslint", ".", "--max-warnings=0"]),
        ("type_check", ["npx", "tsc", "--noEmit"]),
        ("security_audit", ["npm", "audit", "--audit-level=high"]),
    ],
    "rust": [
        ("lint_clippy", ["cargo", "clippy", "--", "-D", "warnings"]),
        ("type_check", ["cargo", "check"]),
    ],
    "go": [
        ("lint_vet", ["go", "vet", "./..."]),
    ],
}


class ValidationEngine:
    """Runs static analysis, lint, and security checks for a repository."""

    async def validate(self, repo_path: str, language: str) -> ValidationReport:
        """Run all applicable validation checks.

        Args:
            repo_path: Absolute path to the repository.
            language: Primary programming language.

        Returns:
            ValidationReport aggregating all check results.
        """
        checks = _VALIDATION_MAP.get(language.lower(), [])
        results: list[ValidationResult] = []

        for check_name, cmd in checks:
            log.info("running_check", check=check_name, language=language)
            rc, stdout, stderr = await run_command(cmd, repo_path)
            results.append(
                ValidationResult(
                    check_name=check_name,
                    passed=rc == 0,
                    output=(stdout + stderr)[:2000],
                    details={"returncode": rc},
                )
            )

        all_passed = all(r.passed for r in results) if results else True
        health = (
            10.0 if all_passed else max(0.0, 10.0 - sum(1 for r in results if not r.passed) * 2)
        )

        return ValidationReport(
            all_passed=all_passed,
            results=results,
            health_score=health,
        )
