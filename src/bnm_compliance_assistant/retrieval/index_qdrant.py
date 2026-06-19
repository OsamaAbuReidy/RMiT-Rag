from __future__ import annotations

from pathlib import Path
import argparse
import uuid

from qdrant_client import QdrantClient, models

from bnm_compliance_assistant.config.settings import settings
from bnm_compliance_assistant.retrieval.bm25 import (
    DEFAULT_CHUNKS_PATH,
    chunk_search_text,
    load_chunks,
)
from bnm_compliance_assistant.retrieval.embeddings import batched, configured_embedding_dimensions, create_embedder


UPSERT_BATCH_SIZE = 64


def qdrant_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"bnm-compliance-assistant:{chunk_id}"))


def payload_from_chunk(chunk: dict) -> dict:
    return {
        "id": chunk["id"],
        "document": chunk["document"],
        "source_file": chunk.get("source_file"),
        "page_number": chunk.get("page_number"),
        "part": chunk.get("part"),
        "section_title": chunk.get("section_title"),
        "subheading": chunk.get("subheading"),
        "appendix": chunk.get("appendix"),
        "clause": chunk.get("clause"),
        "tag": chunk.get("tag"),
        "item": chunk.get("item"),
        "outline_title": chunk.get("outline_title"),
        "outline_level": chunk.get("outline_level"),
        "outline_page_number": chunk.get("outline_page_number"),
        "text": chunk.get("text") or "",
    }


def recreate_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )


def build_points(chunks: list[dict], vectors: list[list[float]]) -> list[models.PointStruct]:
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must have the same length")

    return [
        models.PointStruct(
            id=qdrant_point_id(chunk["id"]),
            vector=vector,
            payload=payload_from_chunk(chunk),
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]


def index_chunks(
    client: QdrantClient,
    embedder,
    chunks: list[dict],
    collection_name: str,
    vector_size: int,
    upsert_batch_size: int = UPSERT_BATCH_SIZE,
) -> None:
    recreate_collection(client, collection_name, vector_size)

    for chunk_batch in batched(chunks, upsert_batch_size):
        texts = [chunk_search_text(chunk) for chunk in chunk_batch]
        vectors = embedder.embed_texts(texts)
        points = build_points(chunk_batch, vectors)
        client.upsert(collection_name=collection_name, points=points)


def main() -> None:
    parser = argparse.ArgumentParser(description="Index processed chunks into Qdrant.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH, help="Path to chunks JSONL")
    parser.add_argument("--qdrant-url", default=settings.qdrant_url, help="Qdrant URL")
    parser.add_argument("--collection", default=settings.qdrant_collection, help="Qdrant collection name")
    parser.add_argument(
        "--vector-size",
        type=int,
        default=configured_embedding_dimensions(),
        help="Embedding vector size",
    )
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    client = QdrantClient(url=args.qdrant_url)
    embedder = create_embedder()

    index_chunks(
        client=client,
        embedder=embedder,
        chunks=chunks,
        collection_name=args.collection,
        vector_size=args.vector_size,
    )
    print(f"Indexed {len(chunks)} chunks into Qdrant collection '{args.collection}'")


if __name__ == "__main__":
    main()
