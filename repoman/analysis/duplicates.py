"""Duplicate issue detection via semantic similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from elasticsearch import AsyncElasticsearch

from repoman.elasticsearch.constants import ISSUES_INDEX


@dataclass(slots=True)
class DuplicateIssueGroup:
    representative_issue_id: str
    issue_ids: list[str]
    max_similarity: float


def _connected_components(edges: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    groups: list[set[str]] = []

    for node in edges:
        if node in seen:
            continue
        stack = [node]
        comp: set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.add(cur)
            stack.extend(list(edges.get(cur, set()) - seen))
        if len(comp) > 1:
            groups.append(comp)
    return groups


async def find_duplicate_issue_groups(
    es: AsyncElasticsearch,
    *,
    repo_full_name: str,
    threshold: float = 0.85,
    per_issue_k: int = 5,
) -> list[DuplicateIssueGroup]:
    """Detect potential duplicate open issues within a repo.

    Args:
        es: Elasticsearch client.
        repo_full_name: Owner/repo.
        threshold: Similarity threshold for grouping.
        per_issue_k: Neighbors to fetch per issue.

    Returns:
        List of DuplicateIssueGroup.
    """
    resp = await es.search(
        index=ISSUES_INDEX,
        size=500,
        query={
            "bool": {
                "filter": [
                    {"term": {"repo_full_name": repo_full_name}},
                    {"term": {"state": "open"}},
                ]
            }
        },
        source_includes=["issue_id", "body_embedding"],
    )
    hits = (resp.get("hits") or {}).get("hits") or []
    issues: list[dict[str, Any]] = [h.get("_source") for h in hits if h.get("_source")]
    issues = [i for i in issues if i.get("issue_id") and i.get("body_embedding")]

    edges: dict[str, set[str]] = {i["issue_id"]: set() for i in issues}
    max_sim: dict[tuple[str, str], float] = {}

    for issue in issues:
        issue_id = issue["issue_id"]
        vec = issue["body_embedding"]
        knn_resp = await es.search(
            index=ISSUES_INDEX,
            size=per_issue_k,
            knn={
                "field": "body_embedding",
                "query_vector": vec,
                "k": per_issue_k,
                "num_candidates": 100,
                "filter": {
                    "bool": {
                        "filter": [
                            {"term": {"repo_full_name": repo_full_name}},
                            {"term": {"state": "open"}},
                        ],
                        "must_not": [{"term": {"issue_id": issue_id}}],
                    }
                },
            },
            source_includes=["issue_id"],
        )

        for hit in (knn_resp.get("hits") or {}).get("hits") or []:
            other = (hit.get("_source") or {}).get("issue_id")
            sim = float(hit.get("_score") or 0.0)
            if not other or sim < threshold:
                continue
            edges.setdefault(issue_id, set()).add(other)
            edges.setdefault(other, set()).add(issue_id)
            key = tuple(sorted((issue_id, other)))
            max_sim[key] = max(max_sim.get(key, 0.0), sim)

    components = _connected_components(edges)
    groups: list[DuplicateIssueGroup] = []
    for comp in components:
        sorted_ids = sorted(comp)
        rep = sorted_ids[0]
        best = 0.0
        for i in range(len(sorted_ids)):
            for j in range(i + 1, len(sorted_ids)):
                best = max(best, max_sim.get((sorted_ids[i], sorted_ids[j]), 0.0))

        groups.append(
            DuplicateIssueGroup(
                representative_issue_id=rep,
                issue_ids=sorted_ids,
                max_similarity=round(best, 4),
            )
        )

    return groups
