"""Embedding generation utilities.

RepoMan's Elasticsearch indices expect fixed-dimension vectors (default: 384).

The default provider is a deterministic hash-based encoder so the system can work
without heavyweight ML dependencies. If you want higher-quality embeddings, set
`EMBEDDING_PROVIDER=sentence_transformers` and install `sentence-transformers`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from hashlib import blake2b

import structlog

from repoman.config import Settings

log = structlog.get_logger()

DEFAULT_VECTOR_DIMS = 384


class EmbeddingEncoder:
    """Protocol-like base for encoders."""

    def encode(self, text: str) -> list[float]:
        raise NotImplementedError


@dataclass(slots=True)
class HashEmbeddingEncoder(EmbeddingEncoder):
    """Feature-hashing style encoder.

    This is not a semantic embedding model. It exists to provide a consistent
    vector representation for local development, tests, and lightweight usage.
    """

    dims: int

    _token_re = re.compile(r"[A-Za-z0-9_]+")

    def encode(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        tokens = (t.lower() for t in self._token_re.findall(text or ""))
        for tok in tokens:
            h = blake2b(tok.encode("utf-8"), digest_size=8).digest()
            n = int.from_bytes(h, "big")
            idx = n % self.dims
            sign = 1.0 if (n & 1) == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


class SentenceTransformersEncoder(EmbeddingEncoder):
    """Sentence-transformers based encoder."""

    def __init__(self, model_name: str, *, dims: int) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers is not installed. Install it and retry."
            ) from exc

        self._model = SentenceTransformer(model_name)
        self._dims = dims

    def encode(self, text: str) -> list[float]:  # pragma: no cover
        embedding = self._model.encode([text or ""], normalize_embeddings=True)[0]
        vec = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        if len(vec) != self._dims:
            raise RuntimeError(f"Expected {self._dims} dims, got {len(vec)}")
        return [float(v) for v in vec]


def create_encoder(config: Settings) -> EmbeddingEncoder:
    """Create an embedding encoder from settings."""
    provider = (config.embedding_provider or "hash").strip().lower()
    if provider == "sentence_transformers":
        log.info("embedding_provider", provider=provider, model=config.embedding_model)
        return SentenceTransformersEncoder(config.embedding_model, dims=config.embedding_dims)

    if provider != "hash":
        log.warning("unknown_embedding_provider", provider=provider, fallback="hash")
    return HashEmbeddingEncoder(dims=config.embedding_dims)
