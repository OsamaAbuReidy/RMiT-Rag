# Operations

## Prerequisites

- Python 3.11 or newer
- Docker Desktop with the Linux engine running
- Gemini API credentials
- Source PDFs listed in `docs/source_documents.md`

## Environment

Create a local environment file from `.env.example`. Never commit `.env`.

Required for the default pipeline:

```dotenv
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_EMBEDDING_DIMENSIONS=1536
GEMINI_GENERATION_MODEL=gemini-3.5-flash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=bnm_compliance_chunks
```

## Build the Corpus

Place both PDFs in `data/raw/`, using the filenames recorded in the source register.

```powershell
python -m bnm_compliance_assistant.ingestion.extract_pages
python -m bnm_compliance_assistant.ingestion.extract_outlines
python -m bnm_compliance_assistant.ingestion.chunk_pages
python -m bnm_compliance_assistant.ingestion.inspect_chunks
```

Generated artifacts are written to `data/processed/` and are not committed.

## Start and Index Qdrant

```powershell
docker compose up -d qdrant
python -m bnm_compliance_assistant.retrieval.index_qdrant
```

Re-run indexing after changing chunks, embedding model, embedding dimensions, or the
collection schema. Keep the Qdrant client and server versions compatible.

## Run the Application

```powershell
uvicorn bnm_compliance_assistant.api.main:app --reload
```

- UI: `http://127.0.0.1:8000/`
- Health check: `GET http://127.0.0.1:8000/health`
- Answer endpoint: `POST http://127.0.0.1:8000/answer`

Example request:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/answer `
  -ContentType "application/json" `
  -Body '{"question":"what should banks do when online banking is partially down","top_k":5}'
```

## Verification

```powershell
python -m pytest
python -m ruff check .
python -m bnm_compliance_assistant.retrieval.evaluate_bm25 --top-k 3
python -m bnm_compliance_assistant.retrieval.evaluate_hybrid --top-k 3
python -m bnm_compliance_assistant.retrieval.evaluate_rerank --top-k 3 --fail-under 1.0
python -m bnm_compliance_assistant.answering.evaluate_answers --top-k 5
```

The dense, hybrid, reranked, and answer evaluations require the configured external
services. Answer evaluation sends prompts and retrieved regulatory text to Gemini and
can incur usage charges.

## Troubleshooting

### Qdrant connection fails

Confirm Docker Desktop's Linux engine is running, then check `docker compose ps` and
`http://localhost:6333/healthz`.

### Qdrant version warning

Align the Docker image tag in `docker-compose.yml` with the installed `qdrant-client`
minor version. Do not suppress compatibility checks as a long-term fix.

### Gemini quota or authentication failure

Verify `GEMINI_API_KEY`, account billing/quota, and the configured model names. Rotate
any key that has been pasted into chat, logs, screenshots, or committed history.

### Reranker is slow on first use

The first request downloads the Hugging Face model. Later requests use the local cache;
CPU inference is expected to add latency.

### Retrieval quality changes after re-indexing

Confirm the chunk count and collection dimensions, then run all retrieval evaluations
before accepting the new index.
