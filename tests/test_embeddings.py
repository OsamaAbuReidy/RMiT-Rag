import pytest

from bnm_compliance_assistant.retrieval import embeddings
from bnm_compliance_assistant.retrieval.embeddings import batched, configured_embedding_dimensions


def test_batched_splits_items() -> None:
    assert list(batched(["a", "b", "c", "d", "e"], 2)) == [["a", "b"], ["c", "d"], ["e"]]


def test_batched_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        list(batched(["a"], 0))


def test_configured_embedding_dimensions_for_deepseek(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings.settings, "embedding_provider", "deepseek")
    monkeypatch.setattr(embeddings.settings, "deepseek_embedding_dimensions", 1024)

    assert configured_embedding_dimensions() == 1024


def test_deepseek_provider_requires_embedding_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings.settings, "embedding_provider", "deepseek")
    monkeypatch.setattr(embeddings.settings, "deepseek_embedding_model", None)

    with pytest.raises(ValueError, match="DEEPSEEK_EMBEDDING_MODEL"):
        embeddings.create_embedder()
