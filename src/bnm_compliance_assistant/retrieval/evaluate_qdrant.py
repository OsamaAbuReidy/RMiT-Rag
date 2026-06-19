from __future__ import annotations

import argparse
from pathlib import Path

from bnm_compliance_assistant.retrieval.evaluate_bm25 import DEFAULT_EVAL_PATH, evaluate, load_cases
from bnm_compliance_assistant.retrieval.qdrant_search import QdrantRetriever


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Qdrant dense retrieval against smoke cases.")
    parser.add_argument("--eval", type=Path, default=DEFAULT_EVAL_PATH, help="Evaluation JSONL path")
    parser.add_argument("--top-k", type=int, default=3, help="Top-k cutoff")
    parser.add_argument("--fail-under", type=float, default=0.0, help="Fail if top-k accuracy is below this value")
    args = parser.parse_args()

    retriever = QdrantRetriever.from_settings()
    cases = load_cases(args.eval)
    report = evaluate(retriever, cases, top_k=args.top_k)

    print(f"Qdrant retrieval smoke evaluation: {report['top_k_hits']}/{report['total']} top-{args.top_k}")
    print(f"Top-1 accuracy: {report['top_1_accuracy']:.2%}")
    print(f"Top-{args.top_k} accuracy: {report['top_k_accuracy']:.2%}")

    failed = [case for case in report["cases"] if not case["passed"]]
    if failed:
        print("\nFailed cases")
        print("------------")
        for case in failed:
            print(case)

    if report["top_k_accuracy"] < args.fail_under:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
