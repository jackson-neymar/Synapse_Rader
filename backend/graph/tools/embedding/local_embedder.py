import logging

from sentence_transformers import SentenceTransformer

from .base import BaseEmbedder

logger = logging.getLogger(__name__)


class LocalEmbedder(BaseEmbedder):
    def __init__(self, model_path: str, device: str = "cpu"):
        logger.info(f"Loading local embedding model: {model_path} (device={device})")
        self._model = SentenceTransformer(model_path, device=device)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info(f"Local embedder ready, dimension={self._dimension}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
