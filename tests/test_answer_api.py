from fastapi.testclient import TestClient

from bnm_compliance_assistant.answering.answer import AnswerResponse, Citation, Source
from bnm_compliance_assistant.api.main import app, get_answer_service


class FakeAnswerService:
    def answer(self, question: str, top_k: int | None = None) -> AnswerResponse:
        return AnswerResponse(
            question=question,
            answer="A financial institution must respond promptly. [S1]",
            refused=False,
            citations=[
                Citation(
                    source_id="S1",
                    document="rmit",
                    page_number=21,
                    clause="10.35",
                    tag="S",
                    appendix=None,
                )
            ],
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
                    text="S 10.35 During an interruption of digital services...",
                )
            ],
        )


def test_answer_endpoint_returns_structured_response() -> None:
    app.dependency_overrides[get_answer_service] = lambda: FakeAnswerService()
    client = TestClient(app)

    response = client.post(
        "/answer",
        json={"question": "what should banks do when online banking is down", "top_k": 3},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "what should banks do when online banking is down"
    assert payload["refused"] is False
    assert payload["citations"][0]["source_id"] == "S1"
    assert payload["sources"][0]["id"] == "rmit_p21_c10_35"


def test_answer_endpoint_rejects_empty_question() -> None:
    app.dependency_overrides[get_answer_service] = lambda: FakeAnswerService()
    client = TestClient(app)

    response = client.post("/answer", json={"question": "", "top_k": 3})

    app.dependency_overrides.clear()

    assert response.status_code == 422
