from bnm_compliance_assistant.ingestion.chunk_pages import chunk_pages


def test_chunk_pages_handles_inline_and_standalone_tags() -> None:
    pages = [
        {
            "document": "rmit",
            "source_file": "sample.pdf",
            "page_number": 3,
            "text": "\n".join(
                [
                    "## **10 Operational resilience**",
                    "- **S** 10.31 A financial institution shall do the first thing.",
                    "   - (a) supporting detail",
                    "**G**",
                    "- 10.32 A financial institution may do the second thing.",
                ]
            ),
        }
    ]

    chunks = chunk_pages(pages)

    assert len(chunks) == 2
    assert chunks[0]["clause"] == "10.31"
    assert chunks[0]["tag"] == "S"
    assert chunks[0]["section_title"] == "10 Operational resilience"
    assert "supporting detail" in chunks[0]["text"]
    assert chunks[1]["clause"] == "10.32"
    assert chunks[1]["tag"] == "G"


def test_chunk_pages_skips_document_preface_pages() -> None:
    pages = [
        {
            "document": "amlcft_fi",
            "source_file": "sample.pdf",
            "page_number": 3,
            "text": "- 1.1 This should be skipped.",
        },
        {
            "document": "amlcft_fi",
            "source_file": "sample.pdf",
            "page_number": 4,
            "text": "- 1.1 This should be included.",
        },
    ]

    chunks = chunk_pages(pages)

    assert len(chunks) == 1
    assert chunks[0]["document"] == "amlcft_fi"
    assert chunks[0]["page_number"] == 4
