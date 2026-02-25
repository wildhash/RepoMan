"""Pattern extraction from pipeline runs."""

from __future__ import annotations

from repoman.core.state import AgentAuditReport


def extract_patterns(audit_reports: list[AgentAuditReport]) -> list[dict]:
    """Extract recurring patterns from audit reports.

    Args:
        audit_reports: List of audit reports from a run.

    Returns:
        List of pattern dicts with category, severity, and count.
    """
    counts: dict[tuple, int] = {}
    for report in audit_reports:
        for issue in report.critical_issues + report.major_issues + report.minor_issues:
            key = (issue.category, issue.severity)
            counts[key] = counts.get(key, 0) + 1

    return [
        {"category": cat, "severity": sev, "count": cnt}
        for (cat, sev), cnt in sorted(counts.items(), key=lambda x: -x[1])
    ]
