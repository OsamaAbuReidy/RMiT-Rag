import pytest

from bnm_compliance_assistant.answering.answer import (
    AnswerService,
    ContextBuilder,
    ModelAnswer,
    ModelCitation,
)
from bnm_compliance_assistant.retrieval.bm25 import SearchResult


class FakeRetriever:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.requested_top_k = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        self.requested_top_k = top_k
        return self.results[:top_k]


class FakeAnswerClient:
    def __init__(self, answer: ModelAnswer) -> None:
        self.answer_payload = answer
        self.question = None
        self.context = None

    def generate(self, question: str, context: str) -> ModelAnswer:
        self.question = question
        self.context = context
        return self.answer_payload


def result(id_: str = "rmit_p21_c10_35", tag: str | None = "S") -> SearchResult:
    return SearchResult(
        score=1.23,
        id=id_,
        document="rmit",
        page_number=21,
        part="PART B POLICY REQUIREMENTS",
        section_title="10 Technology Operations Management",
        subheading="Service Availability",
        appendix=None,
        clause="10.35",
        tag=tag,
        item=None,
        text="S 10.35 During an interruption of digital services, respond promptly.",
    )


def service(results: list[SearchResult], model_answer: ModelAnswer) -> AnswerService:
    return AnswerService(
        retriever=FakeRetriever(results),
        answer_client=FakeAnswerClient(model_answer),
        context_builder=ContextBuilder(),
        default_top_k=5,
    )


def test_context_builder_preserves_metadata_and_source_ids() -> None:
    context = ContextBuilder().build([result()])

    assert context.sources[0].source_id == "S1"
    assert context.sources[0].id == "rmit_p21_c10_35"
    assert context.sources[0].document == "rmit"
    assert context.sources[0].page_number == 21
    assert context.sources[0].clause == "10.35"
    assert context.sources[0].tag == "S"
    assert "source_id: S1" in context.text
    assert "clause: 10.35" in context.text


def test_answer_service_returns_structured_response_with_citations() -> None:
    answer_service = service(
        [result()],
        ModelAnswer(
            answer="A financial institution must respond promptly during disruption. [S1]",
            refused=False,
            citations=[ModelCitation(source_id="S1")],
        ),
    )

    response = answer_service.answer("online banking is down", top_k=3)

    assert response.refused is False
    assert response.citations[0].source_id == "S1"
    assert response.citations[0].document == "rmit"
    assert response.citations[0].clause == "10.35"
    assert response.sources[0].tag == "S"


def test_answer_service_returns_refusal_when_no_sources() -> None:
    answer_service = service(
        [],
        ModelAnswer(answer="unused", refused=False, citations=[ModelCitation(source_id="S1")]),
    )

    response = answer_service.answer("unknown topic")

    assert response.refused is True
    assert response.citations == []
    assert response.sources == []


def test_answer_service_rejects_invalid_citation_ids() -> None:
    answer_service = service(
        [result()],
        ModelAnswer(answer="Invalid citation.", refused=False, citations=[ModelCitation(source_id="S99")]),
    )

    response = answer_service.answer("online banking is down")

    assert response.refused is True
    assert "S99" in response.answer
    assert response.citations == []
    assert response.sources[0].source_id == "S1"


def test_answer_service_rejects_uncited_non_refusal_answer() -> None:
    answer_service = service(
        [result()],
        ModelAnswer(answer="No citations.", refused=False, citations=[]),
    )

    response = answer_service.answer("online banking is down")

    assert response.refused is True
    assert "did not include citations" in response.answer


def test_answer_service_keeps_guidance_metadata_in_sources() -> None:
    answer_service = service(
        [result(tag="G")],
        ModelAnswer(
            answer="This is guidance. [S1]",
            refused=False,
            citations=[ModelCitation(source_id="S1")],
        ),
    )

    response = answer_service.answer("guidance question")

    assert response.sources[0].tag == "G"
    assert response.citations[0].tag == "G"


def test_answer_service_rejects_empty_question() -> None:
    answer_service = service(
        [result()],
        ModelAnswer(answer="unused", refused=False, citations=[ModelCitation(source_id="S1")]),
    )

    with pytest.raises(ValueError, match="question must not be empty"):
        answer_service.answer("   ")
