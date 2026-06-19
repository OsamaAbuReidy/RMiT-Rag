from dataclasses import dataclass

from bnm_compliance_assistant.retrieval.qdrant_search import QdrantRetriever


@dataclass
class FakeHit:
    score: float
    payload: dict


class FakeClient:
    def __init__(self) -> None:
        self.query = None
        self.limit = None

    def query_points(self, *, collection_name: str, query: list[float], limit: int, with_payload: bool):
        self.query = query
        self.limit = limit
        assert collection_name == "chunks"
        assert with_payload is True
        return type(
            "FakeQueryResponse",
            (),
            {
                "points": [
                    FakeHit(
                        score=0.9,
                        payload={
                            "id": "rmit_p20_c10_31",
                            "document": "rmit",
                            "page_number": 20,
                            "part": "PART B POLICY REQUIREMENTS",
                            "section_title": "10 Technology Operations Management",
                            "subheading": "Service Availability",
                            "appendix": None,
                            "clause": "10.31",
                            "tag": "S",
                            "item": None,
                            "text": "S 10.31 text",
                        },
                    )
                ]
            },
        )()


class FakeEmbedder:
    def embed_query(self, query: str) -> list[float]:
        assert query == "service availability"
        return [0.1, 0.2, 0.3]


def test_qdrant_retriever_maps_hits_to_search_results() -> None:
    client = FakeClient()
    retriever = QdrantRetriever(client=client, embedder=FakeEmbedder(), collection_name="chunks")

    results = retriever.search("service availability", top_k=3)

    assert client.query == [0.1, 0.2, 0.3]
    assert client.limit == 3
    assert len(results) == 1
    assert results[0].id == "rmit_p20_c10_31"
    assert results[0].clause == "10.31"
    assert results[0].tag == "S"
