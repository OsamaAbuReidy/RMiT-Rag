from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import re

from bnm_compliance_assistant.retrieval.bm25 import BM25Retriever, SearchResult
from bnm_compliance_assistant.retrieval.qdrant_search import QdrantRetriever


CLAUSE_QUERY_RE = re.compile(r"\b\d+[A-Z]?(?:\.\d+[A-Z]?)+\b", re.IGNORECASE)


def extract_clause_queries(query: str) -> set[str]:
    return {match.group(0) for match in CLAUSE_QUERY_RE.finditer(query)}


def normalize_scores(results: list[SearchResult]) -> dict[str, float]:
    if not results:
        return {}

    max_score = max(result.score for result in results)
    if max_score <= 0:
        return {result.id: 0 for result in results}

    return {result.id: result.score / max_score for result in results}


@dataclass
class HybridRetriever:
    bm25: BM25Retriever
    dense: QdrantRetriever
    bm25_weight: float = 0.4
    dense_weight: float = 0.6
    exact_clause_boost: float = 1.0
    candidate_multiplier: int = 5

    @classmethod
    def from_settings(cls) -> "HybridRetriever":
        return cls(
            bm25=BM25Retriever.from_jsonl(),
            dense=QdrantRetriever.from_settings(),
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        candidate_k = max(top_k * self.candidate_multiplier, top_k)
        bm25_results = self.bm25.search(query, top_k=candidate_k)
        dense_results = self.dense.search(query, top_k=candidate_k)

        bm25_scores = normalize_scores(bm25_results)
        dense_scores = normalize_scores(dense_results)
        result_by_id = {result.id: result for result in dense_results}
        result_by_id.update({result.id: result for result in bm25_results})

        clause_queries = extract_clause_queries(query)
        scored_results = []
        for chunk_id, result in result_by_id.items():
            score = (
                self.bm25_weight * bm25_scores.get(chunk_id, 0)
                + self.dense_weight * dense_scores.get(chunk_id, 0)
            )
            if result.clause and result.clause in clause_queries:
                score += self.exact_clause_boost
            scored_results.append(
                SearchResult(
                    score=score,
                    id=result.id,
                    document=result.document,
                    page_number=result.page_number,
                    part=result.part,
                    section_title=result.section_title,
                    subheading=result.subheading,
                    appendix=result.appendix,
                    clause=result.clause,
                    tag=result.tag,
                    item=result.item,
                    text=result.text,
                )
            )

        return sorted(scored_results, key=lambda result: result.score, reverse=True)[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search chunks with hybrid BM25 + Qdrant retrieval.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()

    retriever = HybridRetriever.from_settings()
    results = retriever.search(args.query, top_k=args.top_k)

    for rank, result in enumerate(results, start=1):
        preview = result.text.replace("\n", " ")
        if len(preview) > 500:
            preview = preview[:497] + "..."
        print(f"\n#{rank} score={result.score:.3f}")
        print(
            json.dumps(
                {
                    "id": result.id,
                    "document": result.document,
                    "page_number": result.page_number,
                    "part": result.part,
                    "section_title": result.section_title,
                    "subheading": result.subheading,
                    "appendix": result.appendix,
                    "clause": result.clause,
                    "tag": result.tag,
                    "item": result.item,
                    "preview": preview,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
