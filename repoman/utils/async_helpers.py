"""Async utility helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


async def gather_with_concurrency(n: int, *tasks: Awaitable[Any]) -> list[Any]:
    """Run coroutines with a maximum concurrency limit.

    Args:
        n: Maximum number of concurrent tasks.
        *tasks: Coroutines to execute.

    Returns:
        List of results in the same order as tasks.
    """
    semaphore = asyncio.Semaphore(n)

    async def bounded(task: Awaitable[Any]) -> Any:
        async with semaphore:
            return await task

    return list(await asyncio.gather(*[bounded(t) for t in tasks]))


async def retry(
    fn: Callable[[], Awaitable[Any]],
    retries: int = 3,
    base_delay: float = 2.0,
) -> Any:
    """Retry an async callable with exponential backoff.

    Args:
        fn: Async callable to retry.
        retries: Number of attempts.
        base_delay: Initial delay in seconds (doubles each retry).

    Returns:
        Result of the first successful call.

    Raises:
        Exception: The last exception raised after all retries are exhausted.
    """
    last_exc: Exception | None = None
    delay = base_delay
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
    raise last_exc  # type: ignore[misc]
