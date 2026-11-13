import hashlib
from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np

from mnemos.core.config import get_settings


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-random normalized embedding provider based on text hash.
    Generates exact reproducible embeddings without network or external model overhead.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension
        self._query_cache: dict[str, list[float]] = {}
        self._cache_max_size = 2048

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_single(self, text: str) -> list[float]:
        # Hash text and seed a local random generator
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        clean = text.strip()
        if clean in self._query_cache:
            return self._query_cache[clean]
        vec = self._embed_single(clean)
        if len(self._query_cache) >= self._cache_max_size:
            for k in list(self._query_cache.keys())[:256]:
                del self._query_cache[k]
        self._query_cache[clean] = vec
        return vec


class FastEmbedProvider(BaseEmbeddingProvider):
    """Local ONNX embedding provider using FastEmbed."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimension: int = 384):
        from fastembed import TextEmbedding
        self._model = TextEmbedding(model_name=model_name)
        self._dim = dimension
        self._query_cache: dict[str, list[float]] = {}
        self._cache_max_size = 2048

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = list(self._model.embed(texts))
        return [e.tolist() for e in embeddings]

    def embed_query(self, text: str) -> list[float]:
        clean = text.strip()
        if clean in self._query_cache:
            return self._query_cache[clean]
        embeddings = list(self._model.embed([clean]))
        vec = embeddings[0].tolist()
        if len(self._query_cache) >= self._cache_max_size:
            for k in list(self._query_cache.keys())[:256]:
                del self._query_cache[k]
        self._query_cache[clean] = vec
        return vec


_provider_instance: BaseEmbeddingProvider | None = None


def get_embedding_provider() -> BaseEmbeddingProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    settings = get_settings()
    if settings.embedding_provider == "mock":
        _provider_instance = MockEmbeddingProvider(dimension=settings.embedding_dimension)
    elif settings.embedding_provider == "fastembed":
        try:
            _provider_instance = FastEmbedProvider(
                model_name=settings.embedding_model,
                dimension=settings.embedding_dimension,
            )
        except Exception:
            # Fallback to deterministic mock if offline or download error
            _provider_instance = MockEmbeddingProvider(dimension=settings.embedding_dimension)
    else:
        _provider_instance = MockEmbeddingProvider(dimension=settings.embedding_dimension)

    return _provider_instance
