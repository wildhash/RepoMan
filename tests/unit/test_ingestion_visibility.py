"""Regression coverage for immediate ingest -> analyze/search reads."""

from __future__ import annotations

from collections import defaultdict
from unittest.mock import AsyncMock

import pytest

from repoman.config import Settings
from repoman.elasticsearch.constants import ISSUES_INDEX, REPOSITORIES_INDEX
from repoman.elasticsearch.ingestion import ElasticsearchIngestionService
from repoman.embeddings.encoder import HashEmbeddingEncoder


@pytest.mark.parametrize("with_issue", [False, True])
async def test_ingested_documents_are_searchable_before_return(
    monkeypatch, with_issue: bool
) -> None:
    # Model Elasticsearch's refresh boundary: acknowledged writes are not yet searchable.
    pending: dict[str, list[dict]] = defaultdict(list)
    visible: dict[str, list[dict]] = defaultdict(list)
    es = AsyncMock()

    async def index(*, index, document, **kwargs):
        pending[index].append(document)

    async def bulk_index(client, actions):
        for action in actions:
            pending[action["_index"]].append(action["_source"])

    async def refresh(*, index):
        indices = index.split(",") if isinstance(index, str) else index
        for name in indices:
            visible[name].extend(pending.pop(name, []))

    async def search(*, index, **kwargs):
        return {"hits": {"hits": [{"_source": doc} for doc in visible[index]]}}

    es.index.side_effect = index
    es.indices.refresh.side_effect = refresh
    es.search.side_effect = search
    monkeypatch.setattr("repoman.elasticsearch.ingestion.bulk_index", bulk_index)

    github = AsyncMock()
    github.get_repo.return_value = {"id": 1, "name": "pilot", "full_name": "owner/pilot"}
    github.get_readme_text.return_value = "Pilot repository"
    github.file_exists.return_value = False
    github.get_contributors.return_value = []
    github.list_issues.return_value = [{"id": 2, "title": "Broken build"}] if with_issue else []
    service = ElasticsearchIngestionService(
        Settings(_env_file=None), es=es, github=github, encoder=HashEmbeddingEncoder(dims=8)
    )

    result = await service.ingest_repo("owner/pilot")

    # This is the lookup used by analyze_repo, immediately after ingest_repo in the CLI.
    assert (await service._get_repo_doc("owner/pilot"))["full_name"] == "owner/pilot"
    assert len(visible[REPOSITORIES_INDEX]) == 1
    assert len(visible[ISSUES_INDEX]) == result["issues_indexed"] == int(with_issue)
