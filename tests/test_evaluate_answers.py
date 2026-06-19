from bnm_compliance_assistant.answering.answer import AnswerResponse, Citation, Source
from bnm_compliance_assistant.answering.evaluate_answers import (
    AnswerCase,
    citation_matches,
    evaluate,
    load_cases,
    required_citation_hit,
)


class FakeAnswerer:
    def __init__(self, responses: dict[str, AnswerResponse]) -> None:
        self.responses = responses
        self.requested_top_k = None

    def answer(self, question: str, top_k: int | None = None) -> AnswerResponse:
        self.requested_top_k = top_k
        return self.responses[question]


def response(
    question: str,
    refused: bool = False,
    citation: Citation | None = None,
    answer: str = "Standard 10.35 requires customer communication.",
) -> AnswerResponse:
    citations = [] if citation is None else [citation]
    return AnswerResponse(
        question=question,
        answer=answer,
        refused=refused,
        citations=citations,
        sources=[
            Source(
                source_id="S1",
                id="rmit_p21_c10_35",
                document="rmit",
                page_number=21,
                clause="10.35",
                tag="S",
                appendix=None,
                score=1.0,
                text="text",
            )
        ],
    )


def citation(**overrides: object) -> Citation:
    values = {
        "source_id": "S1",
        "document": "rmit",
        "page_number": 21,
        "clause": "10.35",
        "tag": "S",
        "appendix": None,
    }
    values.update(overrides)
    return Citation(**values)


def test_load_cases() -> None:
    cases = load_cases()

    assert cases
    assert cases[0].id == "rmit_outage_response"


def test_citation_matches_clause_candidate() -> None:
    assert citation_matches(citation(), {"document": "rmit", "clause": "10.35"})
    assert not citation_matches(citation(), {"document": "rmit", "clause": "10.34"})


def test_citation_matches_appendix_by_substring() -> None:
    appendix_citation = citation(clause=None, appendix="Appendix 11 Fraud Detection Standards")

    assert citation_matches(appendix_citation, {"document": "rmit", "appendix": "Fraud Detection"})


def test_required_citation_hit_accepts_any_expected_candidate() -> None:
    citations = [citation(document="amlcft_fi", clause="14C.14.1")]

    assert required_citation_hit(
        citations,
        [
            {"document": "amlcft_fi", "clause": "14A.13.1"},
            {"document": "amlcft_fi", "clause": "14C.14.1"},
        ],
    )


def test_evaluate_passes_matching_answer() -> None:
    case = AnswerCase(
        id="case",
        query="question",
        expected_refused=False,
        expected_citations=[{"document": "rmit", "clause": "10.35"}],
        required_terms=["Standard"],
    )
    answerer = FakeAnswerer({"question": response("question", citation=citation())})

    report = evaluate(answerer, [case], top_k=3)

    assert answerer.requested_top_k == 3
    assert report["passed"] == 1
    assert report["accuracy"] == 1.0


def test_evaluate_fails_missing_required_term() -> None:
    case = AnswerCase(
        id="case",
        query="question",
        expected_refused=False,
        expected_citations=[{"document": "rmit", "clause": "10.35"}],
        required_terms=["missing"],
    )
    answerer = FakeAnswerer({"question": response("question", citation=citation())})

    report = evaluate(answerer, [case], top_k=3)

    assert report["passed"] == 0
    assert report["cases"][0]["missing_required_terms"] == ["missing"]


def test_evaluate_passes_expected_refusal() -> None:
    case = AnswerCase(id="case", query="question", expected_refused=True)
    answerer = FakeAnswerer(
        {
            "question": response(
                "question",
                refused=True,
                answer="I am unable to answer from the supplied evidence.",
            )
        }
    )

    report = evaluate(answerer, [case], top_k=3)

    assert report["passed"] == 1
