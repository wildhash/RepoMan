"""Custom exceptions for Elasticsearch integration."""

from __future__ import annotations


class ElasticsearchNotConfiguredError(RuntimeError):
    """Raised when Elasticsearch settings are not configured."""


class ElasticsearchUnavailableError(RuntimeError):
    """Raised when Elasticsearch cannot be reached."""
