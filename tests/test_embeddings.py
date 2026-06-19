import pytest

from bnm_compliance_assistant.retrieval.embeddings import batched


def test_batched_splits_items() -> None:
    assert list(batched(["a", "b", "c", "d", "e"], 2)) == [["a", "b"], ["c", "d"], ["e"]]


def test_batched_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        list(batched(["a"], 0))
