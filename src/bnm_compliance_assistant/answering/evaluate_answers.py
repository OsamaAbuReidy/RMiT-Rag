from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
import argparse
import json

from bnm_compliance_assistant.answering.answer import AnswerResponse, AnswerService, Citation


DEFAULT_ANSWER_EVAL_PATH = Path("data/eval/answer_smoke.jsonl")


@dataclass(frozen=True)
class AnswerCase:
    id: str
    query: str
    expected_refused: bool
    expected_citations: list[dict] = field(default_factory=list)
    required_terms: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)
    notes: str | None = None


class Answerer(Protocol):
    def answer(self, question: str, top_k: int | None = None) -> AnswerResponse:
        ...


def load_cases(path: Path = DEFAULT_ANSWER_EVAL_PATH) -> list[AnswerCase]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        payload = json.loads(line)
        cases.append(
            AnswerCase(
                id=payload["id"],
                query=payload["query"],
                expected_refused=payload["expected_refused"],
                expected_citations=payload.get("expected_citations", []),
                required_terms=payload.get("required_terms", []),
                forbidden_terms=payload.get("forbidden_terms", []),
                notes=payload.get("notes"),
            )
        )
    return cases


def citation_matches(citation: Citation, expected: dict) -> bool:
    for key, value in expected.items():
        citation_value = getattr(citation, key)
        if citation_value is None:
            return False
        if key == "appendix":
            if value.lower() not in citation_value.lower():
                return False
        elif citation_value != value:
            return False
    return True


def required_citation_hit(citations: list[Citation], expected: list[dict]) -> bool:
    if not expected:
        return True
    return any(
        citation_matches(citation, candidate)
        for citation in citations
        for candidate in expected
    )


def missing_required_terms(answer: str, required_terms: list[str]) -> list[str]:
    answer_lower = answer.lower()
    return [term for term in required_terms if term.lower() not in answer_lower]


def present_forbidden_terms(answer: str, forbidden_terms: list[str]) -> list[str]:
    answer_lower = answer.lower()
    return [term for term in forbidden_terms if term.lower() in answer_lower]


def evaluate(answerer: Answerer, cases: list[AnswerCase], top_k: int) -> dict:
    evaluated_cases = []
    for case in cases:
        response = answerer.answer(case.query, top_k=top_k)
        refusal_matches = response.refused == case.expected_refused
        citation_hit = response.refused or required_citation_hit(
            response.citations,
            case.expected_citations,
        )
        missing_terms = missing_required_terms(response.answer, case.required_terms)
        forbidden_terms = present_forbidden_terms(response.answer, case.forbidden_terms)
        passed = refusal_matches and citation_hit and not missing_terms and not forbidden_terms
        evaluated_cases.append(
            {
                "id": case.id,
                "query": case.query,
                "expected_refused": case.expected_refused,
                "actual_refused": response.refused,
                "expected_citations": case.expected_citations,
                "actual_citations": [citation.model_dump() for citation in response.citations],
                "citation_hit": citation_hit,
                "missing_required_terms": missing_terms,
                "present_forbidden_terms": forbidden_terms,
                "passed": passed,
                "answer": response.answer,
            }
        )

    total = len(evaluated_cases)
    passed_count = sum(1 for case in evaluated_cases if case["passed"])
    return {
        "total": total,
        "passed": passed_count,
        "accuracy": passed_count / total if total else 0,
        "cases": evaluated_cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate grounded answers against smoke cases.")
    parser.add_argument("--eval", type=Path, default=DEFAULT_ANSWER_EVAL_PATH, help="Evaluation JSONL path")
    parser.add_argument("--top-k", type=int, default=5, help="Retrieved sources to use")
    parser.add_argument("--fail-under", type=float, default=0.0, help="Fail if accuracy is below this value")
    args = parser.parse_args()

    answerer = AnswerService.from_settings()
    cases = load_cases(args.eval)
    report = evaluate(answerer, cases, top_k=args.top_k)

    print(f"Answer smoke evaluation: {report['passed']}/{report['total']} passed")
    print(f"Accuracy: {report['accuracy']:.2%}")

    failed = [case for case in report["cases"] if not case["passed"]]
    if failed:
        print("\nFailed cases")
        print("------------")
        for case in failed:
            print(json.dumps(case, ensure_ascii=False, indent=2))

    if report["accuracy"] < args.fail_under:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
