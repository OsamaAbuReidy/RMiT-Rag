from bnm_compliance_assistant.retrieval.bm25 import SearchResult
from bnm_compliance_assistant.retrieval.hybrid import (
    HybridRetriever,
    extract_clause_queries,
    normalize_scores,
)


class FakeRetriever:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.requested_top_k = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        self.requested_top_k = top_k
        return self.results[:top_k]


def result(id_: str, score: float, clause: str | None = None) -> SearchResult:
    return SearchResult(
        score=score,
        id=id_,
        document="rmit",
        page_number=1,
        part=None,
        section_title=None,
        subheading=None,
        appendix=None,
        clause=clause,
        tag=None,
        item=None,
        text=f"{id_} text",
    )


def test_extract_clause_queries() -> None:
    assert extract_clause_queries("compare 10.31 and 14C.10.15") == {"10.31", "14C.10.15"}


def test_normalize_scores() -> None:
    scores = normalize_scores([result("a", 2), result("b", 1)])

    assert scores == {"a": 1.0, "b": 0.5}


def test_hybrid_boosts_exact_clause_match() -> None:
    bm25 = FakeRetriever([result("exact", 10, clause="10.31")])
    dense = FakeRetriever([result("semantic", 1, clause="10.33")])
    retriever = HybridRetriever(
        bm25=bm25,
        dense=dense,
        exact_clause_boost=1.0,
    )

    results = retriever.search("10.31", top_k=2)

    assert results[0].id == "exact"
    assert results[0].score > results[1].score


def test_hybrid_merges_duplicate_chunk_ids() -> None:
    bm25 = FakeRetriever([result("same", 10, clause="10.31")])
    dense = FakeRetriever([result("same", 0.8, clause="10.31")])
    retriever = HybridRetriever(bm25=bm25, dense=dense)

    results = retriever.search("service availability", top_k=3)

    assert len(results) == 1
    assert results[0].id == "same"
