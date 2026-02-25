"""Unit tests for health scoring."""

from __future__ import annotations

import pytest

from repoman.analysis.health import compute_initial_health_score, compute_weighted_score
from repoman.core.state import RepoSnapshot


def make_snapshot(**kwargs) -> RepoSnapshot:
    """Helper to create a RepoSnapshot with defaults."""
    defaults = dict(url="https://github.com/x/y", name="y", clone_path="/tmp/y")
    defaults.update(kwargs)
    return RepoSnapshot(**defaults)


class TestInitialHealthScore:
    """Tests for heuristic health scoring."""

    def test_empty_repo_score(self) -> None:
        """Empty repo should get base score of 30."""
        s = make_snapshot()
        assert compute_initial_health_score(s) == pytest.approx(30.0)

    def test_readme_adds_points(self) -> None:
        """Having a README should add 10 points."""
        without = compute_initial_health_score(make_snapshot())
        with_readme = compute_initial_health_score(make_snapshot(has_readme=True))
        assert with_readme - without == pytest.approx(10.0)

    def test_tests_add_points(self) -> None:
        """Having tests should add 15 points."""
        without = compute_initial_health_score(make_snapshot())
        with_tests = compute_initial_health_score(make_snapshot(has_tests=True))
        assert with_tests - without == pytest.approx(15.0)

    def test_ci_adds_points(self) -> None:
        """Having CI should add 10 points."""
        without = compute_initial_health_score(make_snapshot())
        with_ci = compute_initial_health_score(make_snapshot(has_ci=True))
        assert with_ci - without == pytest.approx(10.0)

    def test_large_file_count_penalised(self) -> None:
        """More than 1000 files should lower the score."""
        normal = compute_initial_health_score(make_snapshot(total_files=50))
        large = compute_initial_health_score(make_snapshot(total_files=1001))
        assert normal > large

    def test_score_never_negative(self) -> None:
        """Score should never go below 0."""
        s = make_snapshot(total_files=5000)
        assert compute_initial_health_score(s) >= 0.0

    def test_score_never_exceeds_100(self) -> None:
        """Score should never exceed 100."""
        s = make_snapshot(
            has_readme=True, has_tests=True, has_ci=True,
            has_dockerfile=True, has_license=True, has_env_example=True,
            total_files=50,
        )
        assert compute_initial_health_score(s) <= 100.0


class TestWeightedScore:
    """Tests for dimension-weighted scoring."""

    def test_all_tens(self) -> None:
        """All dimensions at 10 should give overall 10."""
        dims = {k: 10.0 for k in ["architecture", "code_quality", "test_coverage", "security",
                                    "documentation", "performance", "maintainability", "deployment_readiness"]}
        assert compute_weighted_score(dims) == pytest.approx(10.0)

    def test_all_zeros(self) -> None:
        """All dimensions at 0 should give overall 0."""
        dims = {k: 0.0 for k in ["architecture", "code_quality", "test_coverage", "security",
                                   "documentation", "performance", "maintainability", "deployment_readiness"]}
        assert compute_weighted_score(dims) == pytest.approx(0.0)

    def test_empty_dims_returns_default(self) -> None:
        """Empty dims dict should default to 5.0 for each dimension."""
        score = compute_weighted_score({})
        assert score == pytest.approx(5.0)
