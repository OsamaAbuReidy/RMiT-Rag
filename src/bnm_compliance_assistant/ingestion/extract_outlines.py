from pathlib import Path
import json
import re

import fitz


OUTPUT_PATH = Path("data/processed/outlines.jsonl")

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

CLAUSE_PREFIX_RE = re.compile(r"^(?P<clause>\d+[A-Z]?(?:\.\d+[A-Z]?)+)\b")
SECTION_PREFIX_RE = re.compile(r"^(?P<section>\d+[A-Z]?)\s+(?P<title>.+)$")
APPENDIX_PREFIX_RE = re.compile(r"^(?P<appendix>APPENDIX\s+\S+)\s*(?P<title>.*)$", re.IGNORECASE)


def write_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def classify_outline_title(title: str) -> dict[str, str | None]:
    normalized = re.sub(r"\s+", " ", title).strip()

    clause_match = CLAUSE_PREFIX_RE.match(normalized)
    if clause_match:
        return {
            "entry_type": "clause",
            "clause": clause_match.group("clause"),
            "section": clause_match.group("clause").split(".")[0],
            "appendix": None,
        }

    appendix_match = APPENDIX_PREFIX_RE.match(normalized)
    if appendix_match:
        return {
            "entry_type": "appendix",
            "clause": None,
            "section": None,
            "appendix": appendix_match.group("appendix").upper(),
        }

    section_match = SECTION_PREFIX_RE.match(normalized)
    if section_match:
        return {
            "entry_type": "section",
            "clause": None,
            "section": section_match.group("section"),
            "appendix": None,
        }

    if normalized.upper().startswith("PART "):
        return {
            "entry_type": "part",
            "clause": None,
            "section": None,
            "appendix": None,
        }

    return {
        "entry_type": "heading",
        "clause": None,
        "section": None,
        "appendix": None,
    }


def json_safe(value: object) -> object:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {key: json_safe(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [json_safe(item) for item in value]
        return str(value)


def extract_document_outline(document: str, path: Path) -> list[dict]:
    pdf = fitz.open(path)
    records = []

    for index, entry in enumerate(pdf.get_toc(simple=False), start=1):
        level, title, page_number, detail = entry
        classification = classify_outline_title(title)
        records.append(
            {
                "document": document,
                "source_file": path.name,
                "outline_index": index,
                "level": level,
                "page_number": page_number,
                "title": re.sub(r"\s+", " ", title).strip(),
                "entry_type": classification["entry_type"],
                "section": classification["section"],
                "clause": classification["clause"],
                "appendix": classification["appendix"],
                "destination": json_safe(detail),
            }
        )

    return records


def main() -> None:
    outlines = []
    for doc in DOCUMENTS:
        outlines.extend(
            extract_document_outline(
                document=doc["document"],
                path=doc["path"],
            )
        )

    write_jsonl(outlines, OUTPUT_PATH)
    print(f"Wrote {len(outlines)} outline entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
