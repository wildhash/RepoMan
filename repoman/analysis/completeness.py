"""Repository completeness analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CompletenessResult:
    missing_elements: list[str]
    completeness_score: float


def compute_completeness(
    *,
    readme_text: str | None,
    has_license: bool,
    has_contributing: bool,
    has_ci_config: bool,
    has_tests: bool,
    has_package_manager_config: bool,
) -> CompletenessResult:
    """Compute a completeness score and missing elements list.

    Args:
        readme_text: README contents if present.
        has_license: Whether a license file exists.
        has_contributing: Whether CONTRIBUTING.md exists.
        has_ci_config: Whether CI config exists (workflows, travis, etc.).
        has_tests: Whether a tests directory exists.
        has_package_manager_config: Whether package manager manifest exists.

    Returns:
        CompletenessResult.
    """
    missing: list[str] = []
    readme_ok = bool(readme_text and len(readme_text.strip()) >= 500)
    if not readme_ok:
        missing.append("README")
    if not has_license:
        missing.append("LICENSE")
    if not has_contributing:
        missing.append("CONTRIBUTING")
    if not has_ci_config:
        missing.append("CI_CONFIG")
    if not has_tests:
        missing.append("TESTS")
    if not has_package_manager_config:
        missing.append("PACKAGE_MANAGER")

    total = 6
    present = total - len(missing)
    score = round((present / total) * 100.0, 2)
    return CompletenessResult(missing_elements=missing, completeness_score=score)
