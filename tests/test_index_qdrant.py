from bnm_compliance_assistant.retrieval.index_qdrant import (
    build_points,
    payload_from_chunk,
    qdrant_point_id,
)


def sample_chunk() -> dict:
    return {
        "id": "rmit_p20_c10_31",
        "document": "rmit",
        "source_file": "pd-rmit-nov25.pdf",
        "page_number": 20,
        "part": "PART B POLICY REQUIREMENTS",
        "section_title": "10 Technology Operations Management",
        "subheading": "Service Availability",
        "appendix": None,
        "clause": "10.31",
        "tag": "S",
        "item": None,
        "outline_title": None,
        "outline_level": None,
        "outline_page_number": None,
        "text": "S 10.31 A financial institution shall enhance service availability.",
    }


def test_qdrant_point_id_is_deterministic_uuid() -> None:
    first = qdrant_point_id("chunk-a")
    second = qdrant_point_id("chunk-a")

    assert first == second
    assert len(first) == 36


def test_payload_from_chunk_preserves_retrieval_fields() -> None:
    payload = payload_from_chunk(sample_chunk())

    assert payload["id"] == "rmit_p20_c10_31"
    assert payload["document"] == "rmit"
    assert payload["clause"] == "10.31"
    assert payload["tag"] == "S"
    assert payload["text"].startswith("S 10.31")


def test_build_points_pairs_chunks_and_vectors() -> None:
    chunk = sample_chunk()
    points = build_points([chunk], [[0.1, 0.2, 0.3]])

    assert len(points) == 1
    assert points[0].payload["id"] == chunk["id"]
    assert points[0].vector == [0.1, 0.2, 0.3]
