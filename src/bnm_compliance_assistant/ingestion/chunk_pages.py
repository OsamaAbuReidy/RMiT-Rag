from __future__ import annotations

from pathlib import Path
import json
import re


INPUT_PATH = Path("data/processed/pages.jsonl")
OUTLINE_INPUT_PATH = Path("data/processed/outlines.jsonl")
OUTPUT_PATH = Path("data/processed/chunks.jsonl")

CONTENT_START_PAGES = {
    "rmit": 3,
    "amlcft_fi": 4,
}

CLAUSE_RE = re.compile(
    r"^\s*-\s+(?:(?:\*\*)?(?P<inline_tag>[SG])(?:\*\*)?\s+)?(?P<clause>\d+[A-Z]?(?:\.\d+[A-Z]?)+)\s+(?P<text>.*)$"
)
STANDALONE_TAG_RE = re.compile(r"^\s*(?:-\s*)?\*\*(?P<tag>[SG])\*\*\s*$")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.+?)\s*$")
PAGE_END_RE = re.compile(r"^-{3}\s+end of page\.page_number=\d+\s+-{3}$", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^\d+\s+of\s+\d+\s*$", re.IGNORECASE)
BNM_REF_RE = re.compile(r"^BNM/RH/PD\s+\d+-\d+\s*$", re.IGNORECASE)
ISSUED_ON_RE = re.compile(r"^Issued on:", re.IGNORECASE)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def clean_heading(raw: str) -> str:
    title = raw.strip()
    title = title.replace("*", "").replace("_", "")
    return re.sub(r"\s+", " ", title).strip()


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("**==> picture"):
        return True
    if PAGE_END_RE.match(stripped):
        return True
    if PAGE_NUMBER_RE.match(stripped):
        return True
    if BNM_REF_RE.match(stripped):
        return True
    if ISSUED_ON_RE.match(stripped):
        return True
    return False


def build_outline_clause_index(outlines: list[dict]) -> dict[tuple[str, str], dict]:
    clause_index = {}
    for outline in outlines:
        clause = outline.get("clause")
        if not clause:
            continue
        key = (outline["document"], clause)
        clause_index.setdefault(key, outline)
    return clause_index


def chunk_pages(pages: list[dict], outlines: list[dict] | None = None) -> list[dict]:
    chunks: list[dict] = []
    outline_clause_index = build_outline_clause_index(outlines or [])
    current_heading_by_doc: dict[str, str | None] = {}
    pending_tag_by_doc: dict[str, str | None] = {}
    current_chunk: dict | None = None

    def flush_current() -> None:
        nonlocal current_chunk
        if current_chunk is None:
            return
        current_chunk["text"] = "\n".join(current_chunk.pop("_text_lines")).strip()
        if current_chunk["text"]:
            chunks.append(current_chunk)
        current_chunk = None

    for page in pages:
        document = page["document"]
        page_number = page["page_number"]
        if page_number < CONTENT_START_PAGES[document]:
            continue

        source_file = page["source_file"]
        current_heading_by_doc.setdefault(document, None)
        pending_tag_by_doc.setdefault(document, None)

        for line in (page.get("text") or "").splitlines():
            if is_noise_line(line):
                continue

            heading_match = HEADING_RE.match(line)
            if heading_match:
                current_heading_by_doc[document] = clean_heading(heading_match.group("title"))
                continue

            tag_match = STANDALONE_TAG_RE.match(line)
            if tag_match:
                pending_tag_by_doc[document] = tag_match.group("tag")
                continue

            clause_match = CLAUSE_RE.match(line)
            if clause_match:
                flush_current()
                inline_tag = clause_match.group("inline_tag")
                tag = inline_tag or pending_tag_by_doc[document]
                pending_tag_by_doc[document] = None
                clause = clause_match.group("clause")
                outline = outline_clause_index.get((document, clause))
                current_chunk = {
                    "id": f"{document}_p{page_number}_c{clause.replace('.', '_')}",
                    "document": document,
                    "source_file": source_file,
                    "page_number": page_number,
                    "section_title": current_heading_by_doc[document],
                    "clause": clause,
                    "tag": tag,
                    "outline_title": outline["title"] if outline else None,
                    "outline_level": outline["level"] if outline else None,
                    "outline_page_number": outline["page_number"] if outline else None,
                    "_text_lines": [f"{tag + ' ' if tag else ''}{clause} {clause_match.group('text')}".strip()],
                }
                continue

            if current_chunk is not None and current_chunk["document"] == document:
                current_chunk["_text_lines"].append(line.strip())

    flush_current()
    return chunks


def main() -> None:
    pages = load_jsonl(INPUT_PATH)
    outlines = load_jsonl(OUTLINE_INPUT_PATH) if OUTLINE_INPUT_PATH.exists() else []
    chunks = chunk_pages(pages, outlines)
    write_jsonl(chunks, OUTPUT_PATH)
    print(f"Wrote {len(chunks)} chunks to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
