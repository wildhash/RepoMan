"""Repo direction assessment based on recent issues and PRs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from elasticsearch import AsyncElasticsearch

from repoman.elasticsearch.constants import ISSUES_INDEX


@dataclass(slots=True)
class DirectionAssessment:
    summary: str
    diverges: bool


async def assess_repo_direction(
    es: AsyncElasticsearch,
    *,
    repo_full_name: str,
    repo_topics: list[str],
    repo_description: str,
) -> DirectionAssessment:
    """Assess whether recent work diverges from stated repo purpose."""
    resp = await es.search(
        index=ISSUES_INDEX,
        size=20,
        sort=[{"updated_at": {"order": "desc"}}],
        query={
            "bool": {
                "filter": [
                    {"term": {"repo_full_name": repo_full_name}},
                    {"term": {"state": "closed"}},
                ]
            }
        },
        source_includes=["labels", "is_pull_request", "title"],
    )

    hits = (resp.get("hits") or {}).get("hits") or []
    label_counts: dict[str, int] = {}
    for h in hits:
        src: dict[str, Any] = h.get("_source") or {}
        for label in src.get("labels") or []:
            label_counts[label] = label_counts.get(label, 0) + 1

    top_labels = sorted(label_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    labels_list = [k for k, _ in top_labels]
    topics_set = {t.lower() for t in repo_topics or []}

    diverges = bool(labels_list) and not any(label.lower() in topics_set for label in labels_list)
    label_str = ", ".join(labels_list) if labels_list else "(no labels)"

    summary = (
        f"Recent closed work labels: {label_str}. Topics: {', '.join(repo_topics or []) or '(none)'}. "
        f"Repo description: {repo_description or '(none)'}"
    )
    if diverges:
        summary += " — recent work may diverge from stated purpose."

    return DirectionAssessment(summary=summary, diverges=diverges)
