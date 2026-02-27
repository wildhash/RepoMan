"""Elasticsearch client initialization and FastAPI integration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch

from repoman.config import Settings
from repoman.elasticsearch.errors import ElasticsearchNotConfiguredError


def create_es_client(config: Settings) -> AsyncElasticsearch:
    """Create an AsyncElasticsearch client from settings.

    Args:
        config: Application settings.

    Returns:
        AsyncElasticsearch client.

    Raises:
        ElasticsearchNotConfiguredError: If no URL or Cloud ID is configured.
    """
    if not (config.elasticsearch_url or config.elasticsearch_cloud_id):
        raise ElasticsearchNotConfiguredError(
            "Elasticsearch is not configured. Set ELASTICSEARCH_URL or ELASTICSEARCH_CLOUD_ID."
        )

    kwargs: dict = {
        "request_timeout": 30,
        "retry_on_timeout": True,
        "max_retries": 3,
    }
    if config.elasticsearch_api_key:
        kwargs["api_key"] = config.elasticsearch_api_key

    if config.elasticsearch_cloud_id:
        return AsyncElasticsearch(cloud_id=config.elasticsearch_cloud_id, **kwargs)

    return AsyncElasticsearch(hosts=[config.elasticsearch_url], **kwargs)


@asynccontextmanager
async def es_lifespan(config: Settings) -> AsyncIterator[AsyncElasticsearch | None]:
    """FastAPI lifespan helper for Elasticsearch.

    If Elasticsearch is not configured, yields None.

    Args:
        config: Application settings.

    Yields:
        AsyncElasticsearch client or None.
    """
    client: AsyncElasticsearch | None
    try:
        client = create_es_client(config)
    except ElasticsearchNotConfiguredError:
        client = None

    try:
        yield client
    finally:
        if client is not None:
            await client.close()
