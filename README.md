# BNM Compliance Onboarding Assistant

A portfolio RAG project for answering onboarding questions about selected Bank Negara Malaysia regulatory documents, starting with RMiT and AML/CFT.

The initial implementation focus is:

1. Structure-aware ingestion from source PDFs.
2. Hybrid retrieval using dense vectors plus BM25.
3. Grounded answer generation with citations.
4. Verification for citation support and Standard (S) versus Guidance (G) fidelity.
5. Repeatable evaluation and CI gates.

See [implementation_plan.md](implementation_plan.md) for the full project plan.

## Project Structure

```text
.
├── data/
│   ├── raw/              # Source PDFs, not committed by default
│   └── processed/        # Parsed chunks and generated indexes, not committed by default
├── docs/                 # Architecture, operations, and handover docs
├── src/
│   └── bnm_compliance_assistant/
│       ├── api/          # FastAPI application and routes
│       ├── config/       # Runtime settings
│       ├── evaluation/   # Golden-set and adversarial evaluation
│       ├── ingestion/    # PDF parsing and chunk creation
│       ├── orchestration/# LangGraph workflow
│       ├── retrieval/    # Dense, sparse, and hybrid retrieval
│       └── verification/ # Groundedness and S/G checks
└── tests/                # Unit and integration tests
```

## Current Status

Repository scaffolding is in place. Implementation starts with ingestion and retrieval.
