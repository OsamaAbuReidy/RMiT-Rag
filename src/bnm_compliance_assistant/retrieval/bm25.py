from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import re

from rank_bm25 import BM25Okapi


DEFAULT_CHUNKS_PATH = Path("data/processed/chunks.jsonl")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[A-Za-z0-9.]+)?")


@dataclass(frozen=True)
class SearchResult:
    score: float
    id: str
    document: str
    page_number: int
    part: str | None
    section_title: str | None
    subheading: str | None
    appendix: str | None
    clause: str | None
    tag: str | None
    item: str | None
    text: str

    @classmethod
    def from_chunk(cls, score: float, chunk: dict) -> "SearchResult":
        return cls(
            score=score,
            id=chunk["id"],
            document=chunk["document"],
            page_number=chunk["page_number"],
            part=chunk.get("part"),
            section_title=chunk.get("section_title"),
            subheading=chunk.get("subheading"),
            appendix=chunk.get("appendix"),
            clause=chunk.get("clause"),
            tag=chunk.get("tag"),
            item=chunk.get("item"),
            text=chunk.get("text") or "",
        )

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "id": self.id,
            "document": self.document,
            "page_number": self.page_number,
            "part": self.part,
            "section_title": self.section_title,
            "subheading": self.subheading,
            "appendix": self.appendix,
            "clause": self.clause,
            "tag": self.tag,
            "item": self.item,
            "text": self.text,
        }


def load_chunks(path: Path = DEFAULT_CHUNKS_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def chunk_search_text(chunk: dict) -> str:
    fields = [
        chunk.get("document"),
        chunk.get("part"),
        chunk.get("section_title"),
        chunk.get("subheading"),
        chunk.get("appendix"),
        chunk.get("clause"),
        chunk.get("tag"),
        chunk.get("item"),
        chunk.get("outline_title"),
        chunk.get("text"),
    ]
    return " ".join(str(field) for field in fields if field)


class BM25Retriever:
    def __init__(self, chunks: list[dict]) -> None:
        if not chunks:
            raise ValueError("BM25Retriever requires at least one chunk")

        self.chunks = chunks
        self.tokenized_chunks = [tokenize(chunk_search_text(chunk)) for chunk in chunks]
        self.index = BM25Okapi(self.tokenized_chunks)

    @classmethod
    def from_jsonl(cls, path: Path = DEFAULT_CHUNKS_PATH) -> "BM25Retriever":
        return cls(load_chunks(path))

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self.index.get_scores(query_tokens)
        if not any(score > 0 for score in scores):
            query_token_set = set(query_tokens)
            scores = [
                len(query_token_set.intersection(chunk_tokens))
                for chunk_tokens in self.tokenized_chunks
            ]
        ranked_indices = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)

        results = []
        for index in ranked_indices[:top_k]:
            score = float(scores[index])
            if score <= 0:
                continue
            results.append(SearchResult.from_chunk(score=score, chunk=self.chunks[index]))

        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Search processed chunks with BM25.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH, help="Path to chunks JSONL")
    args = parser.parse_args()

    retriever = BM25Retriever.from_jsonl(args.chunks)
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
