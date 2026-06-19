from __future__ import annotations

from dataclasses import dataclass
import argparse
import json

from qdrant_client import QdrantClient

from bnm_compliance_assistant.config.settings import settings
from bnm_compliance_assistant.retrieval.bm25 import SearchResult
from bnm_compliance_assistant.retrieval.embeddings import OpenAIEmbedder


@dataclass
class QdrantRetriever:
    client: QdrantClient
    embedder: OpenAIEmbedder
    collection_name: str

    @classmethod
    def from_settings(cls) -> "QdrantRetriever":
        return cls(
            client=QdrantClient(url=settings.qdrant_url),
            embedder=OpenAIEmbedder(),
            collection_name=settings.qdrant_collection,
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        vector = self.embedder.embed_query(query)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        hits = response.points

        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                SearchResult(
                    score=float(hit.score),
                    id=payload["id"],
                    document=payload["document"],
                    page_number=payload["page_number"],
                    part=payload.get("part"),
                    section_title=payload.get("section_title"),
                    subheading=payload.get("subheading"),
                    appendix=payload.get("appendix"),
                    clause=payload.get("clause"),
                    tag=payload.get("tag"),
                    item=payload.get("item"),
                    text=payload.get("text") or "",
                )
            )
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Qdrant dense chunk index.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()

    retriever = QdrantRetriever.from_settings()
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
