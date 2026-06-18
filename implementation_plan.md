# Implementation Plan: BNM Compliance Onboarding Assistant

| Field | Value |
|---|---|
| Status | Draft |
| Author | Osama Reidy |
| Last updated | 2026-06-18 |
| Target completion | 4 weeks from kickoff |
| Repository | TBD |

## 1. Summary

The BNM Compliance Onboarding Assistant is a retrieval-augmented, multi-agent assistant designed to help new compliance, audit, and IT-risk staff understand selected Bank Negara Malaysia (BNM) regulatory requirements. The initial corpus covers the Risk Management in Technology (RMiT) policy document and the AML/CFT policy document.

The system answers natural-language questions, grounds each answer in cited source clauses, preserves the distinction between mandatory **Standards (S)** and recommended **Guidance (G)**, and refuses to answer when it cannot find adequate support in the source material.

This is a portfolio project, not a production deployment. It is intentionally scoped like a real regulated-domain system because the key engineering practices are the same: traceable citations, structured retrieval, verification gates, refusal behavior, repeatable evaluation, and documented deployment.

## 2. Problem Statement

New hires in compliance, audit, and IT-risk roles at Malaysian financial institutions need to understand dense regulatory documents before they can work effectively. Naive LLM tooling creates two important risks in this setting:

1. **Vector-only retrieval can miss exact requirements.** Regulatory text depends on clause numbers, defined terms, document structure, and Standard/Guidance tags. Semantic similarity alone can retrieve a related passage while missing the clause that actually governs the question.
2. **Ungrounded generation is unacceptable.** An assistant that presents a Guidance (G) item as a mandatory Standard (S), or invents unsupported obligations, is worse than no assistant. The system needs measurable controls against this failure mode, not just prompt instructions.

The design addresses these risks directly through structure-aware ingestion, hybrid retrieval, explicit verification, citation requirements, and evaluation gates.

## 3. Goals and Non-Goals

### 3.1 Goals

- Answer questions about RMiT and AML/CFT requirements with citations to specific sections, appendices, or clauses.
- Preserve and surface the **Standard (S)** versus **Guidance (G)** distinction in every relevant answer.
- Abstain when retrieved context is insufficient instead of producing unsupported answers.
- Provide a repeatable evaluation pipeline that runs in CI and tracks retrieval quality, groundedness, answer relevance, and refusal behavior.
- Document the system so another engineer can run, evaluate, and deploy it from a clean checkout.

### 3.2 Non-Goals

These items are deliberately out of scope for the four-week version:

- **Kubernetes orchestration.** Docker Compose is sufficient for the demo scale. The architecture should remain portable, but Kubernetes will not be implemented in v1.
- **Fine-tuning.** The system will use prompting, retrieval, and verification rather than model customization.
- **Multi-tenancy, authentication, or user management.** The v1 target is a single-user local or demo deployment.
- **Regulations beyond RMiT and AML/CFT.** Additional BNM, Basel, FATF, or internal policy documents are natural extensions, but not part of v1.
- **Legal sign-off or production compliance use.** The assistant is a study and onboarding aid. Documentation must state that it is not legal advice and not an authoritative compliance decision system.

## 4. Architecture

### 4.1 High-Level Overview

```text
                         +--------------------+
                         |    FastAPI API     |
                         +----------+---------+
                                    |
                                    v
                         +--------------------+
                         |    LangGraph       |
                         |   Orchestrator     |
                         +----------+---------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
              v                     v                     v
    +-------------------+  +-------------------+  +-------------------+
    | Retrieval Agent   |  | Verification      |  | Onboarding        |
    | hybrid search +   |  | Agent             |  | Explainer Agent   |
    | reranking         |  | groundedness +    |  | plain-language    |
    +---------+---------+  | S/G fidelity      |  | rewrite           |
              |            +---------+---------+  +---------+---------+
              v                      |                      |
    +-------------------+            |                      v
    | Qdrant dense      |            |            +-------------------+
    | vectors + BM25    |<-----------+------------| Answer with       |
    | sparse index      |                         | citations/status  |
    +---------+---------+                         +-------------------+
              ^
              |
    +-------------------+
    | Ingestion         |
    | chunk, embed,     |
    | index RMiT +      |
    | AML/CFT           |
    +-------------------+
```

### 4.2 Component Breakdown

**Ingestion pipeline.** Parses the source PDFs into structure-aware chunks. Chunking must preserve the relationship between requirement text, clause identifiers, document hierarchy, and Standard (S) or Guidance (G) tags. Each chunk stores metadata such as `document`, `section`, `appendix`, `clause`, and `tag` so retrieval and citations remain traceable.

**Hybrid retrieval.** Combines dense embedding search with BM25 keyword search. Dense retrieval helps with semantic questions; BM25 recovers exact terminology, clause references, defined terms, and short regulatory phrases. A reranking step combines both signals and returns the most relevant candidate clauses.

**Retrieval Agent.** Owns hybrid search and reranking. It returns top-k candidate clauses with full metadata and citation-ready identifiers, not only similarity scores.

**Verification Agent.** Checks a draft answer against retrieved clauses before the response is returned. It verifies that factual claims are supported, cited requirements preserve their Standard (S) or Guidance (G) status, and confidence is high enough to answer. If support is inadequate, it returns an abstention decision.

**Onboarding Explainer Agent.** Rewrites a verified answer in clear language for a new-hire audience while preserving citations and compliance meaning. It does not add new claims or change the Standard (S) versus Guidance (G) distinction.

**LangGraph orchestrator.** Coordinates retrieval, generation, verification, and explanation as an explicit state graph. If verification fails, the graph can retry retrieval once with a reformulated query before returning an abstention.

### 4.3 Query Flow

1. User submits a question to the FastAPI API.
2. The LangGraph orchestrator invokes the Retrieval Agent.
3. The Retrieval Agent returns candidate clauses from hybrid retrieval and reranking.
4. The generation step drafts an answer using only retrieved context.
5. The Verification Agent checks groundedness, citation support, and Standard (S) versus Guidance (G) fidelity.
6. If verification fails, the orchestrator retries retrieval once or returns an explicit abstention.
7. If verification passes, the Onboarding Explainer Agent rewrites the answer for clarity.
8. The API returns the final answer with citations and verification status.

### 4.4 Technology Choices

| Component | Choice | Rationale |
|---|---|---|
| API layer | FastAPI | Provides async request handling, Pydantic validation, and clear OpenAPI documentation. |
| Orchestration | LangGraph | Supports explicit state transitions, retry paths, and independently testable agent nodes. |
| Vector store | Qdrant via Docker | Provides self-hosted dense vector search with metadata filtering suitable for a compliance-style demo. |
| Sparse retrieval | BM25 | Recovers exact clause numbers, defined terms, and regulatory phrases that dense retrieval can miss. |
| Reranking | Cross-encoder reranker | Resolves disagreements between dense and sparse retrieval results. |
| LLM provider | OpenAI | Keeps the portfolio implementation simple and reproducible while supporting high-quality generation and embeddings. |
| Evaluation | Ragas plus task-specific checks | Measures faithfulness, answer relevance, context precision, context recall, and domain-specific refusal behavior. |
| Containerization | Docker Compose | Fits the v1 deployment scale and keeps local setup reproducible. |
| CI | GitHub Actions | Runs linting, unit tests, and evaluation gates on every push. |
| Deployment target | Azure single VM or App Service | Provides a realistic cloud deployment path without adding orchestration complexity. |

## 5. Evaluation Strategy

Evaluation is a first-class deliverable. The project should demonstrate not only that the assistant can answer sample questions, but that its retrieval, grounding, and refusal behavior can be measured repeatedly.

- **Golden dataset:** 30-50 hand-authored Q&A pairs covering RMiT and AML/CFT. The set should include clause-specific questions, Standard (S) versus Guidance (G) distinction questions, cross-document synthesis questions, and unanswerable questions that should trigger abstention.
- **Ragas metrics:** Faithfulness, Answer Relevancy, Context Precision, and Context Recall.
- **Domain checks:** Additional checks for citation presence, citation resolvability, Standard (S) versus Guidance (G) fidelity, and refusal behavior on unsupported questions.
- **Adversarial tests:** 10-15 prompt-injection or instruction-conflict examples that attempt to override source grounding or misstate Standard (S) versus Guidance (G) requirements.
- **Regression gate:** CI should fail when key metrics drop below the recorded baseline threshold. Thresholds should be set after the first stable Week 3 baseline run, not guessed before the system exists.

## 6. Non-Functional Requirements

- **Traceability:** Every answer must include citations to source sections, appendices, or clauses. If no sufficient citation exists, the system must abstain.
- **Reproducibility:** Ingestion, indexing, API startup, and evaluation must run from a clean checkout using documented commands.
- **Inspection:** Retrieved chunks, citations, verification decisions, and abstention reasons should be inspectable during development and demo runs.
- **Documentation completeness:** The README and handover documentation must be sufficient for another engineer to run and deploy the project without verbal explanation.
- **Version pinning:** Source document versions, model choices, evaluation baselines, and major dependencies must be recorded.

## 7. Milestones

### Week 1: Ingestion and Hybrid Retrieval

**Deliverables**

- Source PDF acquisition and version recording for RMiT and AML/CFT.
- Ingestion script that extracts text into structure-aware chunks.
- Metadata schema for document, section, appendix, clause, and Standard (S) or Guidance (G) tag.
- Qdrant collection populated with embeddings.
- BM25 index over the same chunk corpus.
- Reranking step that combines dense and sparse retrieval results.
- FastAPI endpoint for raw retrieval results, without answer generation.

**Acceptance criteria**

- A 20-query clause-specific spot check retrieves the correct chunk in the top 3 results at least 90% of the time.
- Randomly sampled chunks retain citation metadata and do not separate requirement text from its Standard (S) or Guidance (G) tag.
- A clean checkout can run ingestion and retrieval setup from documented commands.

### Week 2: Multi-Agent Answering Pipeline

**Deliverables**

- LangGraph flow for retrieval, generation, verification, optional retry, and explanation.
- Retrieval, verification, and explainer agents implemented as independently testable units.
- Abstention path for insufficient context or failed verification.
- API endpoint that returns answer text, citations, and verification status.

**Acceptance criteria**

- On 10 held-out manually reviewed questions, answers include citations and preserve Standard (S) versus Guidance (G) wording.
- The Verification Agent flags at least 8 of 10 deliberately corrupted draft answers.
- Unsupported questions return an explicit abstention rather than a fabricated answer.

### Week 3: Evaluation Harness

**Deliverables**

- Versioned golden dataset with 30-50 Q&A examples.
- Evaluation script that runs the assistant against the golden dataset.
- Ragas report with Faithfulness, Answer Relevancy, Context Precision, and Context Recall.
- Domain-specific report for citation presence, citation resolvability, Standard (S) versus Guidance (G) fidelity, and abstention behavior.
- Adversarial prompt-injection test set and results.
- Recorded baseline metrics for CI.

**Acceptance criteria**

- Evaluation runs end to end from a documented command.
- Baseline metrics are committed and explained.
- CI threshold values are set from the first stable baseline run.

### Week 4: Productionization and Documentation

**Deliverables**

- Docker Compose covering the API, Qdrant, and required auxiliary services.
- GitHub Actions workflow for linting, unit tests, and evaluation.
- Azure deployment path using a single VM or App Service.
- README with setup, ingestion, run, evaluation, and deployment instructions.
- Architecture and operational handover documentation covering environment variables, known limitations, troubleshooting, and source document versions.

**Acceptance criteria**

- A person unfamiliar with the project can deploy it from the handover documentation within a target time budget of 30 minutes.
- CI is green and blocks regressions below the evaluation baseline.
- The final demo can answer supported questions with citations and abstain on unsupported questions.

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| PDF extraction loses structure from tables, appendices, or multi-column layouts | Medium | High | Manually inspect parsed chunks against the source PDFs before accepting Week 1; add parser-specific fixes where metadata is wrong. |
| Requirement text is separated from its Standard (S) or Guidance (G) tag | Medium | High | Add chunk validation checks and sampled manual review focused on tag preservation. |
| Hybrid retrieval and reranking add noticeable latency | Low | Medium | Measure retrieval latency during Week 1; document the tradeoff and tune top-k/reranker settings only if the demo becomes slow. |
| Golden dataset is too small for statistically strong conclusions | Medium | Medium | Present metrics as regression and quality indicators, not formal statistical proof. Include qualitative examples in the evaluation report. |
| Scope expands into Kubernetes, fine-tuning, or multi-user features | Medium | High | Treat the non-goals as delivery constraints. Revisit extensions only after Week 4 acceptance criteria are met. |
| BNM republishes or revises source documents during the build window | Low | Low | Pin source document versions in the README and record the access date. Treat later updates as a separate corpus-refresh task. |

## 9. Open Questions

- **AML/CFT source scope:** Confirm in Week 1 whether the public BNM AML/CFT document is complete enough for the corpus or whether a public extract must be used.
- **Abstention threshold:** Set empirically in Week 3 after observing score distributions on the golden dataset.
- **Optional UI:** Keep v1 API-only. Reconsider a Streamlit demo only after Week 4 deliverables are complete.
- **Azure target:** Choose between single VM and App Service during Week 4 based on the simplest reproducible deployment path.

## 10. Definition of Done

The project is complete when ingestion, retrieval, answering, verification, evaluation, CI, Docker Compose, and Azure deployment all run from a clean checkout using documented commands.

The final system must answer supported RMiT and AML/CFT questions with source citations, preserve Standard (S) versus Guidance (G) distinctions, abstain when support is insufficient, and pass the recorded evaluation gates in CI.

The documentation is complete when another engineer can use it to run and deploy the project without help from the original author.
