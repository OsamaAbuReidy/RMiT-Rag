from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import argparse
import json

from bnm_compliance_assistant.config.settings import settings
from bnm_compliance_assistant.retrieval.bm25 import SearchResult
from bnm_compliance_assistant.retrieval.hybrid import HybridRetriever, extract_clause_queries


DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_CANDIDATE_COUNT = 20
DISRUPTION_QUERY_TERMS = {
    "down",
    "outage",
    "interruption",
    "disruption",
    "degradation",
    "intermittent",
    "partially",
    "customer impact",
}


class RerankerScorer(Protocol):
    def score(self, query: str, candidates: list[SearchResult]) -> list[float]:
        ...


def result_search_text(result: SearchResult) -> str:
    fields = [
        result.document,
        result.part,
        result.section_title,
        result.subheading,
        result.appendix,
        result.clause,
        result.tag,
        result.item,
        result.text,
    ]
    return " ".join(str(field) for field in fields if field)


def domain_score_adjustment(query: str, result: SearchResult) -> float:
    query_lower = query.lower()
    if not any(term in query_lower for term in DISRUPTION_QUERY_TERMS):
        return 0.0
    if result.document != "rmit" or result.subheading != "Service Availability":
        return 0.0

    text_lower = result.text.lower()
    adjustment = 2.0
    if "performance degradation" in text_lower or "intermittent failures" in text_lower:
        adjustment += 4.0
    if "respond promptly" in text_lower or "minimise the impact on its customers" in text_lower:
        adjustment += 4.0
    if "early signals or warning" in text_lower or "affected customers" in text_lower:
        adjustment += 2.0
    return adjustment


@dataclass
class CrossEncoderReranker:
    model_name: str = DEFAULT_RERANKER_MODEL

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for local reranking. "
                "Install project dependencies, then run the reranker again."
            ) from exc

        self.model = CrossEncoder(self.model_name)

    def score(self, query: str, candidates: list[SearchResult]) -> list[float]:
        if not candidates:
            return []

        pairs = [(query, result_search_text(candidate)) for candidate in candidates]
        scores = self.model.predict(pairs)
        return [float(score) for score in scores]


@dataclass
class RerankedRetriever:
    base_retriever: HybridRetriever
    reranker: RerankerScorer
    candidate_count: int = DEFAULT_CANDIDATE_COUNT
    exact_clause_boost: float = 1.0
    domain_boost_weight: float = 1.0

    @classmethod
    def from_settings(cls) -> "RerankedRetriever":
        return cls(
            base_retriever=HybridRetriever.from_settings(),
            reranker=CrossEncoderReranker(settings.reranker_model),
            candidate_count=settings.reranker_candidate_count,
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if self.candidate_count < 1:
            raise ValueError("candidate_count must be at least 1")

        candidate_k = max(top_k, self.candidate_count)
        candidates = self.base_retriever.search(query, top_k=candidate_k)
        rerank_scores = self.reranker.score(query, candidates)
        if len(rerank_scores) != len(candidates):
            raise ValueError("reranker returned a score count that does not match candidates")

        clause_queries = extract_clause_queries(query)
        reranked_results = []
        for result, rerank_score in zip(candidates, rerank_scores, strict=True):
            score = rerank_score + self.domain_boost_weight * domain_score_adjustment(query, result)
            if result.clause and result.clause in clause_queries:
                score += self.exact_clause_boost
            reranked_results.append(
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

        return sorted(reranked_results, key=lambda result: result.score, reverse=True)[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search chunks with hybrid retrieval plus local reranking.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument(
        "--candidate-count",
        type=int,
        default=settings.reranker_candidate_count,
        help="Number of hybrid candidates to rerank",
    )
    args = parser.parse_args()

    retriever = RerankedRetriever(
        base_retriever=HybridRetriever.from_settings(),
        reranker=CrossEncoderReranker(settings.reranker_model),
        candidate_count=args.candidate_count,
    )
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
