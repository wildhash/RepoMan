"""Recommendation and action item generation."""

from __future__ import annotations

from dataclasses import dataclass

from repoman.analysis.duplicates import DuplicateIssueGroup


@dataclass(slots=True)
class ActionItem:
    priority: str
    category: str
    description: str
    effort_estimate: str


def generate_action_items(
    *,
    missing_elements: list[str],
    stale_issues_count: int,
    stale_prs_count: int,
    duplicate_groups: list[DuplicateIssueGroup],
    direction_diverges: bool,
) -> list[ActionItem]:
    items: list[ActionItem] = []

    if "README" in missing_elements:
        items.append(
            ActionItem(
                priority="critical",
                category="documentation",
                description="Add a README with project description, setup instructions, and usage examples.",
                effort_estimate="small",
            )
        )
    if "LICENSE" in missing_elements:
        items.append(
            ActionItem(
                priority="high",
                category="documentation",
                description="Add a LICENSE file to clarify usage and contributions.",
                effort_estimate="small",
            )
        )
    if "CI_CONFIG" in missing_elements:
        items.append(
            ActionItem(
                priority="high",
                category="maintenance",
                description="Add CI config (e.g. GitHub Actions) to run tests and lint on PRs.",
                effort_estimate="medium",
            )
        )
    if "TESTS" in missing_elements:
        items.append(
            ActionItem(
                priority="high",
                category="maintenance",
                description="Add a minimal test suite and wire it into CI.",
                effort_estimate="medium",
            )
        )

    if stale_issues_count + stale_prs_count > 0:
        items.append(
            ActionItem(
                priority="high",
                category="maintenance",
                description=(
                    f"Review and respond to stale items (issues: {stale_issues_count}, PRs: {stale_prs_count})."
                ),
                effort_estimate="medium",
            )
        )

    if duplicate_groups:
        example = duplicate_groups[0]
        items.append(
            ActionItem(
                priority="medium",
                category="maintenance",
                description=(
                    "Potential duplicate issues detected — consider consolidating: "
                    + ", ".join(example.issue_ids[:5])
                ),
                effort_estimate="small",
            )
        )

    if direction_diverges:
        items.append(
            ActionItem(
                priority="high",
                category="direction",
                description=(
                    "Recent work appears to diverge from the repo's stated purpose — consider updating "
                    "the description/topics or refocusing the roadmap."
                ),
                effort_estimate="small",
            )
        )

    return items
