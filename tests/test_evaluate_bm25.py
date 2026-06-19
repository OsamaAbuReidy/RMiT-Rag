from bnm_compliance_assistant.retrieval.bm25 import SearchResult
from bnm_compliance_assistant.retrieval.evaluate_bm25 import rank_of_first_match, result_matches


def make_result(**overrides: object) -> SearchResult:
    values = {
        "score": 1.0,
        "id": "chunk",
        "document": "rmit",
        "page_number": 1,
        "part": None,
        "section_title": None,
        "subheading": None,
        "appendix": None,
        "clause": "10.31",
        "tag": "S",
        "item": None,
        "text": "text",
    }
    values.update(overrides)
    return SearchResult(**values)


def test_result_matches_clause_candidate() -> None:
    result = make_result(document="rmit", clause="10.31")

    assert result_matches(result, {"document": "rmit", "clause": "10.31"})
    assert not result_matches(result, {"document": "rmit", "clause": "10.32"})


def test_result_matches_appendix_by_substring() -> None:
    result = make_result(
        document="rmit",
        clause=None,
        appendix="Appendix 11 Fraud Detection Standards",
    )

    assert result_matches(result, {"document": "rmit", "appendix": "Fraud Detection"})


def test_rank_of_first_match_accepts_any_expected_candidate() -> None:
    results = [
        make_result(document="amlcft_fi", clause="14B.11.19"),
        make_result(document="amlcft_fi", clause="14A.9.13"),
    ]

    rank = rank_of_first_match(
        results,
        [
            {"document": "amlcft_fi", "clause": "14A.9.13"},
            {"document": "amlcft_fi", "clause": "14D.9.13"},
        ],
    )

    assert rank == 2
