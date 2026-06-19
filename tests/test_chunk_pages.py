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


def test_chunk_pages_attaches_outline_metadata() -> None:
    pages = [
        {
            "document": "amlcft_fi",
            "source_file": "sample.pdf",
            "page_number": 21,
            "text": "- **S** 10.2.1 Reporting institutions are required to assess risk.",
        }
    ]
    outlines = [
        {
            "document": "amlcft_fi",
            "clause": "10.2.1",
            "title": "10.2.1 Reporting institutions are required to take appropriate steps.",
            "level": 3,
            "page_number": 21,
        }
    ]

    chunks = chunk_pages(pages, outlines)

    assert chunks[0]["outline_title"] == outlines[0]["title"]
    assert chunks[0]["outline_level"] == 3
    assert chunks[0]["outline_page_number"] == 21


def test_rmit_appendix_does_not_bleed_into_last_clause() -> None:
    pages = [
        {
            "document": "rmit",
            "source_file": "sample.pdf",
            "page_number": 40,
            "text": "\n".join(
                [
                    "## **PART C REGULATORY PROCESS**",
                    "## **18 Assessment and Gap Analysis**",
                    "- **S** 18.2 The self-assessment must be submitted to the Bank.",
                ]
            ),
        },
        {
            "document": "rmit",
            "source_file": "sample.pdf",
            "page_number": 41,
            "text": "\n".join(
                [
                    "## **Appendix 1 Storage and Transportation of Sensitive Data in Removable Media**",
                    "Financial institutions must ensure adequate controls.",
                    "1. deploying encryption techniques;",
                    "2. implementing authorised access control;",
                ]
            ),
        },
    ]

    chunks = chunk_pages(pages)

    assert chunks[0]["clause"] == "18.2"
    assert "Appendix 1" not in chunks[0]["text"]
    assert chunks[1]["appendix"] == "Appendix 1 Storage and Transportation of Sensitive Data in Removable Media"
    assert chunks[2]["item"] == "1"
    assert chunks[3]["item"] == "2"


def test_chunk_ids_are_unique_when_appendix_items_repeat() -> None:
    pages = [
        {
            "document": "rmit",
            "source_file": "sample.pdf",
            "page_number": 42,
            "text": "\n".join(
                [
                    "## **Appendix 2 Control Measures on Self-service Terminals (SSTs)**",
                    "## **Cash SST**",
                    "1. first cash item",
                    "## **Non-Cash SST**",
                    "1. first non-cash item",
                ]
            ),
        }
    ]

    chunks = chunk_pages(pages)
    ids = [chunk["id"] for chunk in chunks]

    assert len(ids) == len(set(ids))


def test_repeated_clause_line_after_tag_header_is_merged() -> None:
    pages = [
        {
            "document": "amlcft_fi",
            "source_file": "sample.pdf",
            "page_number": 22,
            "text": "\n".join(
                [
                    "## **PART B AML/CFT/CPF/TFS REQUIREMENTS**",
                    "## **10 Application of Risk-Based Approach**",
                    "## **10.3 ML/TF Risk Control and Mitigation**",
                    "- **S** 10.3.2",
                    "   - 10.3.2 Reporting institutions shall conduct independent control testing.",
                ]
            ),
        }
    ]

    chunks = chunk_pages(pages)

    assert len(chunks) == 1
    assert chunks[0]["clause"] == "10.3.2"
    assert chunks[0]["tag"] == "S"
    assert chunks[0]["text"] == (
        "S 10.3.2 Reporting institutions shall conduct independent control testing."
    )


def test_tag_header_skips_repeated_previous_clause_before_target_body() -> None:
    pages = [
        {
            "document": "amlcft_fi",
            "source_file": "sample.pdf",
            "page_number": 29,
            "text": "\n".join(
                [
                    "- **G** 11.5.5 Previous guidance text.",
                    "- **S** 11.5.6",
                    "   - 11.5.5 Previous guidance text.",
                    "   - 11.5.6 Reporting institutions shall maintain comprehensive records.",
                ]
            ),
        }
    ]

    chunks = chunk_pages(pages)

    assert len(chunks) == 2
    assert chunks[0]["clause"] == "11.5.5"
    assert chunks[0]["tag"] == "G"
    assert chunks[1]["clause"] == "11.5.6"
    assert chunks[1]["tag"] == "S"
    assert chunks[1]["text"] == (
        "S 11.5.6 Reporting institutions shall maintain comprehensive records."
    )
