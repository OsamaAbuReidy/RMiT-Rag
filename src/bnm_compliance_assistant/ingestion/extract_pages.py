from pathlib import Path
import json

import pymupdf4llm


DOCUMENTS = [
    {
        "document": "rmit",
        "path": Path("data/raw/pd-rmit-nov25.pdf"),
    },
    {
        "document": "amlcft_fi",
        "path": Path("data/raw/pd-AMLCFTCPF-TFS-FI-Feb2024-v2.pdf"),
    },
]


def write_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_document_pages(document: str, path: Path) -> list[dict]:
    pages = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,
        page_separators=True,
        show_progress=True,
    )

    records = []
    for page in pages:
        metadata = page.get("metadata", {})
        records.append(
            {
                "document": document,
                "source_file": path.name,
                "page_number": metadata.get("page_number"),
                "text": page.get("text", ""),
                "metadata": metadata,
            }
        )

    return records


def main() -> None:
    all_pages = []

    for doc in DOCUMENTS:
        all_pages.extend(
            extract_document_pages(
                document=doc["document"],
                path=doc["path"],
            )
        )

    write_jsonl(all_pages, Path("data/processed/pages.jsonl"))

    print(f"Wrote {len(all_pages)} pages to data/processed/pages.jsonl")


if __name__ == "__main__":
    main()
