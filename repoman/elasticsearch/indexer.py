"""Bulk indexing helpers."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Iterable
from typing import Any

import structlog
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

log = structlog.get_logger()


async def bulk_index(
    es: AsyncElasticsearch,
    actions: Iterable[dict[str, Any]],
    *,
    max_attempts: int = 5,
    base_backoff_seconds: float = 0.5,
) -> None:
    """Index actions via the Bulk API with exponential backoff.

    Args:
        es: Elasticsearch client.
        actions: Iterable of bulk actions.
        max_attempts: Maximum retry attempts for retriable failures.
        base_backoff_seconds: Base backoff duration.
    """
    attempt = 0
    pending = list(actions)

    while pending:
        attempt += 1
        if attempt > max_attempts:
            raise RuntimeError(f"Bulk indexing failed after {max_attempts} attempts")

        success_count, errors = await async_bulk(
            es, pending, raise_on_error=False, stats_only=False
        )
        if isinstance(errors, int):
            raise RuntimeError("Unexpected async_bulk response: stats_only=True")
        if not errors:
            log.info("es_bulk_indexed", successes=success_count)
            return

        failures: list[dict[str, Any]] = []
        for err in errors:
            action, info = next(iter(err.items()))
            status = info.get("status")
            error = info.get("error")
            data = info.get("data")

            is_retriable = status in (408, 429, 500, 502, 503, 504)
            if is_retriable and data:
                failures.append(
                    {
                        "_op_type": action,
                        "_index": info.get("_index"),
                        "_id": info.get("_id"),
                        "_source": data,
                    }
                )
                continue

            log.error("es_bulk_item_failed", action=action, status=status, error=error)
            raise RuntimeError(f"Bulk item failed: {status} {error}")

        pending = failures
        sleep_for = (base_backoff_seconds * (2 ** (attempt - 1))) + random.random() * 0.1
        log.warning(
            "es_bulk_retry",
            attempt=attempt,
            pending=len(pending),
            successes=success_count,
            sleep_for_seconds=round(sleep_for, 2),
        )
        await asyncio.sleep(sleep_for)
