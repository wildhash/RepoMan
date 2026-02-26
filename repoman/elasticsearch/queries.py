"""Elasticsearch query builders (query DSL only)."""

from __future__ import annotations

from typing import Any

from repoman.elasticsearch.constants import ISSUES_INDEX, REPOSITORIES_INDEX


def repo_full_text_search(
    query: str,
    *,
    language: str | None = None,
    status: str | None = None,
    health_score_min: float | None = None,
    health_score_max: float | None = None,
    has_readme: bool | None = None,
    size: int = 20,
) -> dict[str, Any]:
    filters: list[dict[str, Any]] = []
    if language:
        filters.append({"term": {"language": language}})
    if status:
        filters.append({"term": {"status": status}})
    if has_readme is not None:
        filters.append({"term": {"has_readme": has_readme}})
    if health_score_min is not None or health_score_max is not None:
        range_body: dict[str, Any] = {}
        if health_score_min is not None:
            range_body["gte"] = health_score_min
        if health_score_max is not None:
            range_body["lte"] = health_score_max
        filters.append({"range": {"health_score": range_body}})

    body: dict[str, Any] = {
        "index": REPOSITORIES_INDEX,
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^3", "description", "topics^2"],
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": filters,
            }
        },
        "highlight": {"fields": {"description": {}, "name": {}}},
    }

    return body


def issue_full_text_search(
    query: str,
    *,
    repo_full_name: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
    is_pull_request: bool | None = None,
    size: int = 20,
) -> dict[str, Any]:
    filters: list[dict[str, Any]] = []
    if repo_full_name:
        filters.append({"term": {"repo_full_name": repo_full_name}})
    if state:
        filters.append({"term": {"state": state}})
    if labels:
        filters.append({"terms": {"labels": labels}})
    if is_pull_request is not None:
        filters.append({"term": {"is_pull_request": is_pull_request}})

    return {
        "index": ISSUES_INDEX,
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "body"],
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": filters,
            }
        },
        "highlight": {"fields": {"title": {}, "body": {}}},
    }


def repo_semantic_search(
    query_vector: list[float],
    *,
    k: int = 10,
    num_candidates: int = 100,
) -> dict[str, Any]:
    return {
        "index": REPOSITORIES_INDEX,
        "size": k,
        "knn": {
            "field": "description_embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": num_candidates,
        },
    }


def issue_semantic_search(
    query_vector: list[float],
    *,
    repo_full_name: str | None = None,
    k: int = 10,
    num_candidates: int = 100,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "index": ISSUES_INDEX,
        "size": k,
        "knn": {
            "field": "body_embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": num_candidates,
        },
    }

    if repo_full_name:
        body["query"] = {"term": {"repo_full_name": repo_full_name}}

    return body
