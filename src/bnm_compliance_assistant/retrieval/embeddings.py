from __future__ import annotations

from collections.abc import Iterable

from google import genai
from google.genai import types
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


class GeminiEmbedder:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 16,
    ) -> None:
        resolved_api_key = api_key or settings.gemini_api_key
        if not resolved_api_key:
            raise ValueError("GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini")

        self.client = genai.Client(api_key=resolved_api_key)
        self.model = model or settings.gemini_embedding_model
        self.dimensions = dimensions or settings.gemini_embedding_dimensions
        self.batch_size = batch_size

    def _embed_one(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=self.dimensions),
        )
        return list(response.embeddings[0].values)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for batch in batched(texts, self.batch_size):
            embeddings.extend(self._embed_one(text) for text in batch)
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def create_embedder(batch_size: int = 64) -> OpenAIEmbedder | GeminiEmbedder:
    provider = settings.embedding_provider.lower()

    if provider == "openai":
        return OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            batch_size=batch_size,
        )

    if provider == "gemini":
        return GeminiEmbedder(
            api_key=settings.gemini_api_key,
            model=settings.gemini_embedding_model,
            dimensions=settings.gemini_embedding_dimensions,
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
        "Unsupported EMBEDDING_PROVIDER. Expected one of: openai, gemini, openai_compatible"
    )


def configured_embedding_dimensions() -> int:
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        return settings.openai_embedding_dimensions
    if provider == "gemini":
        return settings.gemini_embedding_dimensions
    if provider == "openai_compatible":
        return settings.embedding_dimensions
    raise ValueError(
        "Unsupported EMBEDDING_PROVIDER. Expected one of: openai, gemini, openai_compatible"
    )
