"""Health scoring with 8 weighted dimensions."""

from __future__ import annotations

from repoman.constants import HEALTH_WEIGHTS
from repoman.core.state import RepoSnapshot


def compute_initial_health_score(snapshot: RepoSnapshot) -> float:
    """Compute a heuristic health score for a repository snapshot.

    Uses a base score plus bonuses for key repo hygiene indicators.

    Args:
        snapshot: Repository snapshot to score.

    Returns:
        Health score between 0 and 100.
    """
    score = 30.0
    if snapshot.has_readme:
        score += 10.0
    if snapshot.has_tests:
        score += 15.0
    if snapshot.has_ci:
        score += 10.0
    if snapshot.has_dockerfile:
        score += 5.0
    if snapshot.has_license:
        score += 5.0
    if snapshot.has_env_example:
        score += 5.0
    # Reasonable file size: not too tiny, not too huge
    if 5 <= snapshot.total_files <= 500:
        score += 5.0
    # Penalise very large files count
    if snapshot.total_files > 1000:
        score -= 10.0
    return min(max(score, 0.0), 100.0)


def compute_weighted_score(dimension_scores: dict[str, float]) -> float:
    """Compute the weighted overall score from dimension scores.

    Args:
        dimension_scores: Dict mapping dimension name to 0-10 score.

    Returns:
        Weighted score on a 0-10 scale.
    """
    total = 0.0
    weight_sum = 0.0
    for dim, weight in HEALTH_WEIGHTS.items():
        score = dimension_scores.get(dim, 5.0)
        total += score * weight
        weight_sum += weight
    return round(total / weight_sum if weight_sum > 0 else 0.0, 2)
