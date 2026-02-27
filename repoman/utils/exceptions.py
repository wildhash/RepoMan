"""Exception helpers."""

from __future__ import annotations

import asyncio


def reraise_if_fatal(exc: BaseException) -> None:
    """Reraise cancellation and non-Exception BaseExceptions.

    When using `asyncio.gather(..., return_exceptions=True)`, failures are
    returned as values.

    This helper centralizes the "fatal exception" policy used across the CLI,
    pipeline, and consensus engine.

    Note: this function does not log; call sites are expected to log any context
    before invoking it.

    Pass the original exception instance through; avoid wrapping `CancelledError`
    into another exception type before calling this helper.
    """

    if isinstance(exc, asyncio.CancelledError):
        raise exc

    if not isinstance(exc, Exception):
        raise exc
