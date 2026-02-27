"""Exception helpers."""

from __future__ import annotations

import asyncio


def reraise_if_fatal(exc: BaseException) -> None:
    """Reraise cancellation and non-Exception BaseExceptions.

    When using `asyncio.gather(..., return_exceptions=True)`, failures are
    returned as values. We treat cancellation and other non-standard
    `BaseException` types as fatal and re-raise them.
    """

    if isinstance(exc, asyncio.CancelledError):
        raise exc

    if not isinstance(exc, Exception):
        raise exc
