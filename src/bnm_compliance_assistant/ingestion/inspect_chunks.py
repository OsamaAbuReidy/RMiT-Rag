from __future__ import annotations

from collections import Counter
from pathlib import Path
import json


INPUT_PATH = Path("data/processed/chunks.jsonl")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def print_counter(title: str, counter: Counter) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key, count in counter.most_common():
        print(f"{key}: {count}")


def print_chunk_summary(chunk: dict) -> None:
    text = (chunk.get("text") or "").replace("\n", " ")
    if len(text) > 260:
        text = text[:257] + "..."
    print(
        json.dumps(
            {
                "id": chunk.get("id"),
                "document": chunk.get("document"),
                "page_number": chunk.get("page_number"),
                "part": chunk.get("part"),
                "section_title": chunk.get("section_title"),
                "subheading": chunk.get("subheading"),
                "appendix": chunk.get("appendix"),
                "clause": chunk.get("clause"),
                "tag": chunk.get("tag"),
                "item": chunk.get("item"),
                "outline_title": chunk.get("outline_title"),
                "text_len": len(chunk.get("text") or ""),
                "preview": text,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def print_chunk_samples(title: str, chunks: list[dict], limit: int = 5) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    if not chunks:
        print("No chunks found.")
        return
    for chunk in chunks[:limit]:
        print_chunk_summary(chunk)


def main() -> None:
    chunks = load_jsonl(INPUT_PATH)
    ids = Counter(chunk["id"] for chunk in chunks)
    duplicate_ids = [chunk_id for chunk_id, count in ids.items() if count > 1]

    print("Chunk Quality Report")
    print("====================")
    print(f"Input: {INPUT_PATH}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Duplicate IDs: {len(duplicate_ids)}")
    if duplicate_ids:
        print("Duplicate ID examples:", ", ".join(duplicate_ids[:10]))

    print_counter("Chunks by document", Counter(chunk.get("document") for chunk in chunks))
    print_counter(
        "Chunks by document and part",
        Counter((chunk.get("document"), chunk.get("part")) for chunk in chunks),
    )
    print_counter(
        "Chunks by document and tag",
        Counter((chunk.get("document"), chunk.get("tag")) for chunk in chunks),
    )

    missing_tag = [
        chunk
        for chunk in chunks
        if chunk.get("clause") and chunk.get("part") in {"PART B POLICY REQUIREMENTS", "PART C REGULATORY PROCESS"}
        and not chunk.get("tag")
    ]
    missing_structure = [
        chunk
        for chunk in chunks
        if not chunk.get("clause")
        and not chunk.get("appendix")
        and chunk.get("document") in {"rmit", "amlcft_fi"}
    ]
    amlcft_missing_outline = [
        chunk
        for chunk in chunks
        if chunk.get("document") == "amlcft_fi"
        and chunk.get("clause")
        and not chunk.get("outline_title")
    ]

    print("\nQuality checks")
    print("--------------")
    print(f"Regulatory clauses missing S/G tag: {len(missing_tag)}")
    print(f"Chunks missing both clause and appendix metadata: {len(missing_structure)}")
    print(f"AML/CFT clause chunks missing outline metadata: {len(amlcft_missing_outline)}")

    sorted_by_length = sorted(chunks, key=lambda chunk: len(chunk.get("text") or ""))
    print_chunk_samples("Shortest chunks", sorted_by_length, limit=8)
    print_chunk_samples("Longest chunks", list(reversed(sorted_by_length)), limit=8)

    print_chunk_samples(
        "RMiT Part B samples",
        [
            chunk
            for chunk in chunks
            if chunk.get("document") == "rmit" and chunk.get("part") == "PART B POLICY REQUIREMENTS"
        ],
    )
    print_chunk_samples(
        "RMiT Part C samples",
        [
            chunk
            for chunk in chunks
            if chunk.get("document") == "rmit" and chunk.get("part") == "PART C REGULATORY PROCESS"
        ],
    )
    print_chunk_samples(
        "RMiT appendix samples",
        [chunk for chunk in chunks if chunk.get("document") == "rmit" and chunk.get("appendix")],
    )
    print_chunk_samples(
        "AML/CFT clauses with outline metadata",
        [
            chunk
            for chunk in chunks
            if chunk.get("document") == "amlcft_fi"
            and chunk.get("clause")
            and chunk.get("outline_title")
        ],
    )
    print_chunk_samples(
        "AML/CFT clauses missing outline metadata",
        amlcft_missing_outline,
    )


if __name__ == "__main__":
    main()
