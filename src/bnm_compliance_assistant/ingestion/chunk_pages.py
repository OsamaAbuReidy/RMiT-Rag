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
    r"^\s*-\s+(?:(?:\*\*(?P<bold_tag>[SG])\*\*|(?P<plain_tag>[SG]))\s+)?(?P<clause>\d+[A-Z]?(?:\.\d+[A-Z]?)+)\s*(?P<text>.*)$"
)
APPENDIX_ITEM_RE = re.compile(r"^\s*(?P<item>\d+)\.\s+(?P<text>.+)$")
STANDALONE_TAG_RE = re.compile(r"^\s*(?:-\s*)?\*\*(?P<tag>[SG])\*\*\s*$")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.+?)\s*$")
BOLD_SECTION_RE = re.compile(r"^\s*\*\*(?P<title>\d+[A-Z]?\s+.+?)\*\*\s*$")
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


def classify_heading(title: str) -> tuple[str, str | None]:
    normalized = clean_heading(title)
    if normalized.upper().startswith("PART "):
        return "part", normalized
    if normalized.upper().startswith("APPENDIX "):
        return "appendix", normalized
    if re.match(r"^\d+[A-Z]?\s+", normalized):
        return "section", normalized
    return "subheading", normalized


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("**==> picture"):
        return True
    if stripped == "Risk Management in Technology":
        return True
    if stripped.startswith(
        "Anti-Money Laundering, Countering Financing of Terrorism, Countering Proliferation Financing"
    ):
        return True
    if stripped == "The rest of the page is intentionally left as blank":
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
    current_part_by_doc: dict[str, str | None] = {}
    current_section_by_doc: dict[str, str | None] = {}
    current_subheading_by_doc: dict[str, str | None] = {}
    current_appendix_by_doc: dict[str, str | None] = {}
    pending_tag_by_doc: dict[str, str | None] = {}
    current_chunk: dict | None = None
    id_counts: dict[str, int] = {}
    emitted_clause_keys: set[tuple[str, str]] = set()

    def reserve_id(base_id: str) -> str:
        count = id_counts.get(base_id, 0)
        id_counts[base_id] = count + 1
        if count == 0:
            return base_id
        return f"{base_id}_{count + 1}"

    def flush_current() -> None:
        nonlocal current_chunk
        if current_chunk is None:
            return
        current_chunk["text"] = "\n".join(current_chunk.pop("_text_lines")).strip()
        if current_chunk["text"]:
            current_chunk["id"] = reserve_id(current_chunk["id"])
            chunks.append(current_chunk)
            if current_chunk.get("clause"):
                emitted_clause_keys.add((current_chunk["document"], current_chunk["clause"]))
        current_chunk = None

    def current_chunk_is_tag_only_clause() -> bool:
        if current_chunk is None or not current_chunk.get("clause"):
            return False
        clause = current_chunk["clause"]
        tag = current_chunk.get("tag")
        return (
            len(current_chunk["_text_lines"]) == 1
            and current_chunk["_text_lines"][0].strip() in {clause, f"{tag} {clause}"}
        )

    for page in pages:
        document = page["document"]
        page_number = page["page_number"]
        if page_number < CONTENT_START_PAGES[document]:
            continue

        source_file = page["source_file"]
        current_part_by_doc.setdefault(document, None)
        current_section_by_doc.setdefault(document, None)
        current_subheading_by_doc.setdefault(document, None)
        current_appendix_by_doc.setdefault(document, None)
        pending_tag_by_doc.setdefault(document, None)

        for line in (page.get("text") or "").splitlines():
            if is_noise_line(line):
                continue

            heading_match = HEADING_RE.match(line)
            bold_section_match = BOLD_SECTION_RE.match(line)
            if heading_match or bold_section_match:
                raw_heading = (
                    heading_match.group("title")
                    if heading_match
                    else bold_section_match.group("title")
                )
                heading_type, heading = classify_heading(raw_heading)
                if heading_type in {"part", "appendix", "section"}:
                    flush_current()
                if heading_type == "part":
                    current_part_by_doc[document] = heading
                    current_section_by_doc[document] = None
                    current_subheading_by_doc[document] = None
                    current_appendix_by_doc[document] = None
                elif heading_type == "appendix":
                    current_part_by_doc[document] = "APPENDICES"
                    current_appendix_by_doc[document] = heading
                    current_section_by_doc[document] = None
                    current_subheading_by_doc[document] = None
                    current_chunk = {
                        "id": f"{document}_appendix_{len(chunks) + 1}",
                        "document": document,
                        "source_file": source_file,
                        "page_number": page_number,
                        "part": current_part_by_doc[document],
                        "section_title": None,
                        "subheading": None,
                        "appendix": heading,
                        "clause": None,
                        "tag": None,
                        "item": None,
                        "outline_title": None,
                        "outline_level": None,
                        "outline_page_number": None,
                        "_text_lines": [heading],
                    }
                elif heading_type == "section":
                    current_section_by_doc[document] = heading
                    current_subheading_by_doc[document] = None
                else:
                    if current_appendix_by_doc[document]:
                        flush_current()
                        current_subheading_by_doc[document] = heading
                        current_chunk = {
                            "id": f"{document}_appendix_{len(chunks) + 1}",
                            "document": document,
                            "source_file": source_file,
                            "page_number": page_number,
                            "part": current_part_by_doc[document],
                            "section_title": None,
                            "subheading": heading,
                            "appendix": current_appendix_by_doc[document],
                            "clause": None,
                            "tag": None,
                            "item": None,
                            "outline_title": None,
                            "outline_level": None,
                            "outline_page_number": None,
                            "_text_lines": [heading],
                        }
                    else:
                        current_subheading_by_doc[document] = heading
                continue

            tag_match = STANDALONE_TAG_RE.match(line)
            if tag_match:
                pending_tag_by_doc[document] = tag_match.group("tag")
                continue

            clause_match = CLAUSE_RE.match(line)
            if clause_match:
                clause = clause_match.group("clause")
                clause_text = clause_match.group("text")
                if (
                    current_chunk is not None
                    and current_chunk["document"] == document
                    and current_chunk.get("clause") == clause
                    and current_chunk_is_tag_only_clause()
                ):
                    current_chunk["_text_lines"] = [
                        f"{current_chunk.get('tag') + ' ' if current_chunk.get('tag') else ''}{clause} {clause_text}".strip()
                    ]
                    continue

                inline_tag = clause_match.group("bold_tag") or clause_match.group("plain_tag")
                if (
                    current_chunk_is_tag_only_clause()
                    and current_chunk is not None
                    and current_chunk.get("clause") != clause
                    and not inline_tag
                ):
                    continue

                if (
                    (document, clause) in emitted_clause_keys
                    and pending_tag_by_doc[document]
                    and not inline_tag
                ):
                    continue

                flush_current()
                tag = inline_tag or pending_tag_by_doc[document]
                pending_tag_by_doc[document] = None
                outline = outline_clause_index.get((document, clause))
                current_chunk = {
                    "id": f"{document}_p{page_number}_c{clause.replace('.', '_')}",
                    "document": document,
                    "source_file": source_file,
                    "page_number": page_number,
                    "part": current_part_by_doc[document],
                    "section_title": current_section_by_doc[document],
                    "subheading": current_subheading_by_doc[document],
                    "appendix": current_appendix_by_doc[document],
                    "clause": clause,
                    "tag": tag,
                    "item": None,
                    "outline_title": outline["title"] if outline else None,
                    "outline_level": outline["level"] if outline else None,
                    "outline_page_number": outline["page_number"] if outline else None,
                    "_text_lines": [f"{tag + ' ' if tag else ''}{clause} {clause_match.group('text')}".strip()],
                }
                continue

            appendix_item_match = APPENDIX_ITEM_RE.match(line)
            if current_appendix_by_doc[document] and appendix_item_match:
                flush_current()
                item = appendix_item_match.group("item")
                appendix_slug = re.sub(r"\W+", "_", current_appendix_by_doc[document].lower()).strip("_")
                current_chunk = {
                    "id": f"{document}_{appendix_slug}_item_{item}",
                    "document": document,
                    "source_file": source_file,
                    "page_number": page_number,
                    "part": current_part_by_doc[document],
                    "section_title": None,
                    "subheading": current_subheading_by_doc[document],
                    "appendix": current_appendix_by_doc[document],
                    "clause": None,
                    "tag": None,
                    "item": item,
                    "outline_title": None,
                    "outline_level": None,
                    "outline_page_number": None,
                    "_text_lines": [f"{item}. {appendix_item_match.group('text')}"],
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
