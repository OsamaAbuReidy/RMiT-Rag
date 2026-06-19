from bnm_compliance_assistant.retrieval.bm25 import SearchResult
from bnm_compliance_assistant.retrieval.rerank import (
    RerankedRetriever,
    domain_score_adjustment,
    result_search_text,
)


class FakeBaseRetriever:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.requested_top_k = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        self.requested_top_k = top_k
        return self.results[:top_k]


class FakeReranker:
    def __init__(self, scores_by_id: dict[str, float]) -> None:
        self.scores_by_id = scores_by_id
        self.queries: list[str] = []
        self.candidate_ids: list[str] = []

    def score(self, query: str, candidates: list[SearchResult]) -> list[float]:
        self.queries.append(query)
        self.candidate_ids = [candidate.id for candidate in candidates]
        return [self.scores_by_id[candidate.id] for candidate in candidates]


def result(
    id_: str,
    score: float,
    clause: str | None = None,
    text: str | None = None,
) -> SearchResult:
    return SearchResult(
        score=score,
        id=id_,
        document="rmit",
        page_number=20,
        part="PART B POLICY REQUIREMENTS",
        section_title="10 Technology Operations Management",
        subheading="Service Availability",
        appendix=None,
        clause=clause,
        tag="S",
        item=None,
        text=text or f"{id_} text",
    )


def test_result_search_text_includes_metadata_and_text() -> None:
    search_text = result_search_text(result("rmit_p20_c10_31", 0.7, clause="10.31"))

    assert "rmit" in search_text
    assert "Service Availability" in search_text
    assert "10.31" in search_text
    assert "rmit_p20_c10_31 text" in search_text


def test_domain_adjustment_boosts_service_availability_disruption_clauses() -> None:
    boosted = result(
        "rmit_p21_c10_35",
        0.1,
        clause="10.35",
        text="During an interruption of digital services, including performance degradation "
        "or intermittent failures, respond promptly to minimise the impact on its customers.",
    )
    unrelated = result(
        "rmit_p20_c10_34",
        0.1,
        clause="10.34",
        text="A financial institution shall prioritise diversity in technology.",
    )

    assert domain_score_adjustment("online banking is partially down", boosted) > (
        domain_score_adjustment("online banking is partially down", unrelated)
    )
    assert domain_score_adjustment("employee screening records", boosted) == 0


def test_reranker_preserves_result_metadata() -> None:
    base_result = result("rmit_p21_c10_35", 0.2, clause="10.35", text="digital service outage")
    retriever = RerankedRetriever(
        base_retriever=FakeBaseRetriever([base_result]),
        reranker=FakeReranker({"rmit_p21_c10_35": 0.99}),
        candidate_count=5,
    )

    reranked = retriever.search("employee screening records", top_k=1)

    assert reranked[0].id == base_result.id
    assert reranked[0].document == base_result.document
    assert reranked[0].page_number == base_result.page_number
    assert reranked[0].clause == base_result.clause
    assert reranked[0].text == base_result.text
    assert reranked[0].score == 0.99


def test_candidate_count_is_respected() -> None:
    base = FakeBaseRetriever([result(f"candidate_{index}", 1) for index in range(10)])
    retriever = RerankedRetriever(
        base_retriever=base,
        reranker=FakeReranker({f"candidate_{index}": float(index) for index in range(10)}),
        candidate_count=7,
    )

    reranked = retriever.search("service availability", top_k=3)

    assert base.requested_top_k == 7
    assert [candidate.id for candidate in reranked] == ["candidate_6", "candidate_5", "candidate_4"]


def test_top_k_larger_than_candidate_count_is_respected() -> None:
    base = FakeBaseRetriever([result(f"candidate_{index}", 1) for index in range(4)])
    retriever = RerankedRetriever(
        base_retriever=base,
        reranker=FakeReranker({f"candidate_{index}": float(index) for index in range(4)}),
        candidate_count=2,
    )

    retriever.search("service availability", top_k=4)

    assert base.requested_top_k == 4


def test_exact_clause_query_keeps_exact_clause_first() -> None:
    base = FakeBaseRetriever(
        [
            result("nearby", 0.9, clause="10.34"),
            result("exact", 0.8, clause="10.31"),
        ]
    )
    retriever = RerankedRetriever(
        base_retriever=base,
        reranker=FakeReranker({"nearby": 0.95, "exact": 0.1}),
        candidate_count=2,
        exact_clause_boost=1.0,
    )

    reranked = retriever.search("10.31", top_k=2)

    assert reranked[0].id == "exact"
    assert reranked[0].score > reranked[1].score
