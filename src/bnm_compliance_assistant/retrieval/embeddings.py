from __future__ import annotations

from collections.abc import Iterable

from openai import OpenAI

from bnm_compliance_assistant.config.settings import settings


def batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


class OpenAIEmbedder:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 64,
    ) -> None:
        resolved_api_key = api_key or settings.openai_api_key
        if not resolved_api_key:
            raise ValueError("OPENAI_API_KEY is required for dense retrieval")

        self.client = OpenAI(api_key=resolved_api_key)
        self.model = model or settings.openai_embedding_model
        self.dimensions = dimensions or settings.openai_embedding_dimensions
        self.batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for batch in batched(texts, self.batch_size):
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            embeddings.extend(item.embedding for item in response.data)
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
