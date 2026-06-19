from bnm_compliance_assistant.retrieval.bm25 import BM25Retriever, tokenize


def test_tokenize_preserves_clause_like_tokens() -> None:
    assert "10.31" in tokenize("What does clause 10.31 require?")
    assert "14c.10.15" in tokenize("14C.10.15")


def test_bm25_retrieves_exact_clause() -> None:
    retriever = BM25Retriever(
        [
            {
                "id": "a",
                "document": "rmit",
                "page_number": 20,
                "clause": "10.31",
                "tag": "S",
                "text": "S 10.31 A financial institution shall enhance service availability.",
            },
            {
                "id": "b",
                "document": "rmit",
                "page_number": 8,
                "clause": "8.1",
                "tag": "S",
                "text": "S 8.1 The board must approve technology risk appetite.",
            },
        ]
    )

    results = retriever.search("10.31", top_k=1)

    assert results[0].id == "a"


def test_bm25_uses_metadata_text() -> None:
    retriever = BM25Retriever(
        [
            {
                "id": "a",
                "document": "rmit",
                "page_number": 37,
                "part": "PART C REGULATORY PROCESS",
                "section_title": "16 Notification for Technology-Related Applications",
                "clause": "16.1",
                "tag": "S",
                "text": "A financial institution must notify the Bank.",
            },
            {
                "id": "b",
                "document": "amlcft_fi",
                "page_number": 29,
                "section_title": "Employee Screening Procedures",
                "clause": "11.5.6",
                "tag": "S",
                "text": "Reporting institutions shall maintain comprehensive records.",
            },
        ]
    )

    results = retriever.search("employee screening records", top_k=1)

    assert results[0].id == "b"
