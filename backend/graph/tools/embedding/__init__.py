import logging

from settings import config

from .base import BaseEmbedder

logger = logging.getLogger(__name__)

_embedder = None  # BaseEmbedder singleton


def get_embedder() -> BaseEmbedder:
    global _embedder
    if _embedder is not None:
        return _embedder

    backend = config.EMBEDDING_BACKEND
    if backend == "local":
        from .local_embedder import LocalEmbedder
        _embedder = LocalEmbedder(
            model_path=config.EMBEDDING_MODEL,
            device=config.EMBEDDING_DEVICE,
        )
    elif backend == "openai":
        from .openai_embedder import OpenAIEmbedder
        _embedder = OpenAIEmbedder(
            model=config.EMBEDDING_MODEL,
            api_key=config.OPENAI_API_KEY,
        )
    else:
        raise ValueError(f"Unknown EMBEDDING_BACKEND: {backend}")

    return _embedder
