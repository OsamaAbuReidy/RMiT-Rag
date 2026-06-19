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
        base_url: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 64,
    ) -> None:
        resolved_api_key = api_key or settings.openai_api_key
        if not resolved_api_key:
            raise ValueError("OPENAI_API_KEY is required for dense retrieval")

        self.client = OpenAI(api_key=resolved_api_key, base_url=base_url)
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


def create_embedder(batch_size: int = 64) -> OpenAIEmbedder:
    provider = settings.embedding_provider.lower()

    if provider == "openai":
        return OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            batch_size=batch_size,
        )

    if provider == "deepseek":
        if not settings.deepseek_embedding_model:
            raise ValueError(
                "DEEPSEEK_EMBEDDING_MODEL is required when EMBEDDING_PROVIDER=deepseek. "
                "DeepSeek's official API docs currently list chat/reasoning models, so confirm "
                "your account has an embeddings-compatible model before indexing."
            )
        return OpenAIEmbedder(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_embedding_model,
            dimensions=settings.deepseek_embedding_dimensions,
            batch_size=batch_size,
        )

    if provider == "openai_compatible":
        return OpenAIEmbedder(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=batch_size,
        )

    raise ValueError(
        "Unsupported EMBEDDING_PROVIDER. Expected one of: openai, deepseek, openai_compatible"
    )


def configured_embedding_dimensions() -> int:
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        return settings.openai_embedding_dimensions
    if provider == "deepseek":
        return settings.deepseek_embedding_dimensions
    if provider == "openai_compatible":
        return settings.embedding_dimensions
    raise ValueError(
        "Unsupported EMBEDDING_PROVIDER. Expected one of: openai, deepseek, openai_compatible"
    )
