import logging

import httpx

from .base import BaseEmbedder

logger = logging.getLogger(__name__)


class OpenAIEmbedder(BaseEmbedder):
    DIMENSIONS = {"text-embedding-3-small": 512, "text-embedding-3-large": 3072}

    def __init__(self, model: str, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._dimension = self.DIMENSIONS.get(model, 512)
        logger.info(f"OpenAI embedder ready, model={model}, dimension={self._dimension}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        return asyncio.run(self._async_embed(texts))

    async def _async_embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
