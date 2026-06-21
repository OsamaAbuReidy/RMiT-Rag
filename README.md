# BNM Compliance Onboarding Assistant

[![CI](https://github.com/OsamaAbuReidy/RMiT-Rag/actions/workflows/ci.yml/badge.svg)](https://github.com/OsamaAbuReidy/RMiT-Rag/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A structure-aware retrieval-augmented generation (RAG) assistant for answering
onboarding questions against selected Bank Negara Malaysia regulatory documents.
The current corpus covers Risk Management in Technology (RMiT) and the
AML/CFT/CPF/TFS policy document for financial institutions.

The project demonstrates the full path from irregular regulatory PDFs to grounded,
cited answers: document-specific parsing, clause-aware chunking, hybrid retrieval,
cross-encoder reranking, Gemini generation, validation, evaluation, and a small web UI.

## Results

Latest local evaluation on the committed smoke sets:

| Check | Result |
| --- | ---: |
| Unit and API tests | 52 passed |
| Ruff | All checks passed |
| BM25 retrieval, top-1 | 77.78% (21/27) |
| BM25 retrieval, top-3 | 85.19% (23/27) |
| Reranked retrieval, top-1 | 85.19% (23/27) |
| Reranked retrieval, top-3 | 100.00% (27/27) |
| Grounded answer smoke evaluation | 100.00% (10/10) |

These are small, project-specific smoke sets rather than production benchmarks. They
are useful regression gates and expose the improvement from lexical retrieval to the
reranked pipeline, but they do not establish production-grade accuracy.

## Architecture

```text
Regulatory PDFs
      |
      v
PyMuPDF4LLM extraction -> outline metadata -> clause-aware chunks
                                              |
                         +--------------------+-------------------+
                         |                                        |
                         v                                        v
                    BM25 index                         Gemini embeddings
                                                              + Qdrant
                         |                                        |
                         +--------------------+-------------------+
                                              v
                                  weighted hybrid candidates
                                              |
                                              v
                                local cross-encoder reranker
                                              |
                                              v
                              evidence context + source metadata
                                              |
                                              v
                                  Gemini grounded generation
                                              |
                                              v
                                citation validation / refusal
                                              |
                                    +---------+---------+
                                    |                   |
                                    v                   v
                               FastAPI API          Web UI / CLI
```

Key design decisions:

- Chunk boundaries follow clauses and appendices instead of fixed token windows.
- BM25 preserves exact clause and terminology lookup.
- Qdrant provides dense semantic retrieval using Gemini embeddings.
- A local cross-encoder reranks the top hybrid candidates without sending regulatory
  text to another hosted reranking service.
- Answers distinguish Standard (S) obligations from Guidance (G), cite retrieved
  source IDs, and refuse when evidence is missing or citations fail validation.

See [docs/architecture.md](docs/architecture.md) for component details and tradeoffs.

## Run Locally

Prerequisites: Python 3.11+, Docker Desktop, a Gemini API key, and the two source PDFs
listed in [docs/source_documents.md](docs/source_documents.md).

```powershell
git clone https://github.com/OsamaAbuReidy/RMiT-Rag.git
cd RMiT-Rag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Add `GEMINI_API_KEY` to `.env`, place the source PDFs in `data/raw/`, then prepare the
corpus and index:

```powershell
python -m bnm_compliance_assistant.ingestion.extract_pages
python -m bnm_compliance_assistant.ingestion.extract_outlines
python -m bnm_compliance_assistant.ingestion.chunk_pages
docker compose up -d qdrant
python -m bnm_compliance_assistant.retrieval.index_qdrant
```

Start the application:

```powershell
uvicorn bnm_compliance_assistant.api.main:app --reload
```

Open `http://127.0.0.1:8000/`. The first reranked query may download the configured
cross-encoder model from Hugging Face.

Full operational commands and troubleshooting are in
[docs/operations.md](docs/operations.md).

## Evaluation

```powershell
python -m pytest
python -m ruff check .
python -m bnm_compliance_assistant.retrieval.evaluate_bm25 --top-k 3
python -m bnm_compliance_assistant.retrieval.evaluate_rerank --top-k 3 --fail-under 1.0
python -m bnm_compliance_assistant.answering.evaluate_answers --top-k 5
```

The answer evaluation calls Gemini and can incur API usage. Retrieval cases are in
`data/eval/retrieval_smoke.jsonl`; answer cases are in
`data/eval/answer_smoke.jsonl`.

## Repository Layout

```text
data/eval/                         committed retrieval and answer smoke sets
data/raw/                          local source PDFs (not committed)
data/processed/                    generated pages and chunks (not committed)
docs/                              architecture, operations, and source register
src/bnm_compliance_assistant/
  answering/                       context building, Gemini generation, validation
  api/                             FastAPI routes and static web UI
  ingestion/                       extraction, outlines, and clause-aware chunking
  retrieval/                       BM25, Qdrant, hybrid retrieval, and reranking
tests/                             unit and API tests
```

## Scope and Limitations

- This is a portfolio and research implementation, not legal or compliance advice.
- The corpus contains two policy documents and is not automatically synchronized with
  later BNM revisions.
- The validator checks citation IDs and response structure; it does not prove every
  generated claim is semantically entailed by its cited text.
- Evaluation sets are intentionally small and need independent domain-expert review,
  broader adversarial coverage, latency testing, and monitoring before production use.
- The local API has no authentication, authorization, rate limiting, audit trail, or
  tenant isolation.
- Source PDFs and generated indexes are excluded from Git because of size and source
  distribution considerations.

The original four-week delivery plan is retained in
[implementation_plan.md](implementation_plan.md).

## License

Code is available under the [MIT License](LICENSE). Regulatory source documents remain
subject to their publishers' terms and are not included in this repository.
