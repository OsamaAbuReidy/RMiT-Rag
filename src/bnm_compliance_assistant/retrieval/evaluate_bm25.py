from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json

from bnm_compliance_assistant.retrieval.bm25 import BM25Retriever, SearchResult


DEFAULT_EVAL_PATH = Path("data/eval/retrieval_smoke.jsonl")


@dataclass(frozen=True)
class RetrievalCase:
    id: str
    query: str
    expected: list[dict]
    notes: str | None = None


def load_cases(path: Path = DEFAULT_EVAL_PATH) -> list[RetrievalCase]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        payload = json.loads(line)
        cases.append(
            RetrievalCase(
                id=payload["id"],
                query=payload["query"],
                expected=payload["expected"],
                notes=payload.get("notes"),
            )
        )
    return cases


def result_matches(result: SearchResult, expected: dict) -> bool:
    for key, value in expected.items():
        result_value = getattr(result, key)
        if result_value is None:
            return False
        if key == "appendix":
            if value.lower() not in result_value.lower():
                return False
        elif result_value != value:
            return False
    return True


def rank_of_first_match(results: list[SearchResult], expected: list[dict]) -> int | None:
    for rank, result in enumerate(results, start=1):
        if any(result_matches(result, candidate) for candidate in expected):
            return rank
    return None


def evaluate(retriever: BM25Retriever, cases: list[RetrievalCase], top_k: int) -> dict:
    evaluated_cases = []
    for case in cases:
        results = retriever.search(case.query, top_k=top_k)
        match_rank = rank_of_first_match(results, case.expected)
        evaluated_cases.append(
            {
                "id": case.id,
                "query": case.query,
                "expected": case.expected,
                "match_rank": match_rank,
                "passed": match_rank is not None,
                "top_results": [
                    {
                        "rank": rank,
                        "score": result.score,
                        "document": result.document,
                        "clause": result.clause,
                        "appendix": result.appendix,
                        "tag": result.tag,
                        "id": result.id,
                    }
                    for rank, result in enumerate(results, start=1)
                ],
            }
        )

    total = len(evaluated_cases)
    top_1 = sum(1 for case in evaluated_cases if case["match_rank"] == 1)
    top_k_hits = sum(1 for case in evaluated_cases if case["match_rank"] is not None)

    return {
        "total": total,
        "top_k": top_k,
        "top_1_hits": top_1,
        "top_k_hits": top_k_hits,
        "top_1_accuracy": top_1 / total if total else 0,
        "top_k_accuracy": top_k_hits / total if total else 0,
        "cases": evaluated_cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate BM25 retrieval against smoke cases.")
    parser.add_argument("--eval", type=Path, default=DEFAULT_EVAL_PATH, help="Evaluation JSONL path")
    parser.add_argument("--chunks", type=Path, default=None, help="Chunks JSONL path")
    parser.add_argument("--top-k", type=int, default=3, help="Top-k cutoff")
    parser.add_argument("--fail-under", type=float, default=0.0, help="Fail if top-k accuracy is below this value")
    args = parser.parse_args()

    retriever = BM25Retriever.from_jsonl(args.chunks) if args.chunks else BM25Retriever.from_jsonl()
    cases = load_cases(args.eval)
    report = evaluate(retriever, cases, top_k=args.top_k)

    print(f"BM25 retrieval smoke evaluation: {report['top_k_hits']}/{report['total']} top-{args.top_k}")
    print(f"Top-1 accuracy: {report['top_1_accuracy']:.2%}")
    print(f"Top-{args.top_k} accuracy: {report['top_k_accuracy']:.2%}")

    failed = [case for case in report["cases"] if not case["passed"]]
    if failed:
        print("\nFailed cases")
        print("------------")
        for case in failed:
            print(json.dumps(case, ensure_ascii=False, indent=2))

    if report["top_k_accuracy"] < args.fail_under:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
