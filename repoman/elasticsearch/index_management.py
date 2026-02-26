"""Elasticsearch index and lifecycle management."""

from __future__ import annotations

import json
from pathlib import Path

import structlog
from elasticsearch import AsyncElasticsearch, NotFoundError

from repoman.elasticsearch.constants import (
    ANALYSIS_DATA_STREAM,
    ANALYSIS_ILM_POLICY,
    ANALYSIS_INDEX_TEMPLATE,
    ISSUES_INDEX,
    REPOSITORIES_INDEX,
)

log = structlog.get_logger()


def _load_mapping(name: str) -> dict:
    path = Path(__file__).parent / "mappings" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


async def ensure_indices(es: AsyncElasticsearch) -> None:
    """Create indices/data streams required by RepoMan.

    Operations are idempotent; existing resources are left untouched.

    Args:
        es: Elasticsearch client.
    """
    await _ensure_index(es, REPOSITORIES_INDEX, _load_mapping("repositories"))
    await _ensure_index(es, ISSUES_INDEX, _load_mapping("issues"))
    await _ensure_analysis_data_stream(es)


async def _ensure_index(es: AsyncElasticsearch, index: str, body: dict) -> None:
    exists = await es.indices.exists(index=index)
    if exists:
        return

    log.info("es_create_index", index=index)
    await es.indices.create(index=index, **body)


async def _ensure_analysis_data_stream(es: AsyncElasticsearch) -> None:
    mapping = _load_mapping("analysis")["mappings"]

    # Create an ILM policy that deletes backing indices after 90 days.
    await es.ilm.put_lifecycle(
        name=ANALYSIS_ILM_POLICY,
        policy={
            "phases": {
                "hot": {"actions": {}},
                "delete": {"min_age": "90d", "actions": {"delete": {}}},
            }
        },
    )

    await es.indices.put_index_template(
        name=ANALYSIS_INDEX_TEMPLATE,
        index_patterns=[f"{ANALYSIS_DATA_STREAM}*"],
        data_stream={},
        template={
            "settings": {"index.lifecycle.name": ANALYSIS_ILM_POLICY},
            "mappings": mapping,
        },
        priority=500,
    )

    try:
        ds_list = await es.indices.get_data_stream(name=ANALYSIS_DATA_STREAM)
    except NotFoundError:
        ds_list = None

    if not ds_list or not ds_list.get("data_streams"):
        log.info("es_create_data_stream", name=ANALYSIS_DATA_STREAM)
        await es.indices.create_data_stream(name=ANALYSIS_DATA_STREAM)
