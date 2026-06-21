# Architecture

## System Boundary

The assistant answers questions only from the locally indexed RMiT and
AML/CFT/CPF/TFS source documents. The runtime path is deliberately small: retrieval,
reranking, context construction, generation, and citation validation are composed by
`AnswerService`. LangGraph and conversational memory are outside the current scope.

## Data Flow

```text
PDF -> page extraction -> outline extraction -> structure-aware chunks
                                                    |
                    +-------------------------------+------------------+
                    |                                                  |
                    v                                                  v
              BM25Retriever                                  QdrantRetriever
                    |                                                  |
                    +---------------- HybridRetriever ----------------+
                                         |
                                  top 20 candidates
                                         |
                              CrossEncoderReranker
                                         |
                                  top-k evidence
                                         |
                                  ContextBuilder
                                         |
                                GeminiAnswerClient
                                         |
                           citation validation/refusal
                                         |
                                   CLI / FastAPI
```

## Ingestion

`pymupdf4llm` extracts page Markdown and metadata. Separate outline extraction captures
PDF bookmarks where they are reliable. The chunker applies document-specific rules:

- RMiT chunks preserve parts, numbered topics, unnumbered subheadings, clauses,
  Standard (S) and Guidance (G) tags, nested list content, and appendices.
- AML/CFT chunks use the document outline and clause identifiers, including nested
  identifiers such as `10.14.1`.
- Stable chunk IDs encode document, page, and clause or appendix identity.

The generated artifacts remain local under `data/processed/`.

## Retrieval

BM25 is the lexical baseline and handles exact terminology and clause references.
Qdrant stores Gemini-generated dense vectors for semantic matching. Hybrid retrieval
combines both result sets through weighted score fusion and retains exact-clause boost
behavior. The local `cross-encoder/ms-marco-MiniLM-L-6-v2` model reranks the top 20
hybrid candidates before returning the final evidence set.

All retrievers return the same `SearchResult` shape so the answering layer is isolated
from retrieval implementation details.

## Answering and Validation

`ContextBuilder` assigns source IDs and renders retrieved metadata and text as bounded
evidence blocks. `GeminiAnswerClient` requests a structured JSON response under rules
that require evidence-only answers, source-ID citations, Standard (S) and Guidance (G)
distinction, and refusal when evidence is insufficient.

`AnswerService` rejects non-refusal responses with no citations or with source IDs that
do not exist in the retrieved set. This is a structural safety check, not full semantic
claim verification.

## Evaluation

The committed retrieval smoke set contains exact-clause, natural-language, appendix,
CDD, STR, and targeted-financial-sanctions cases. The answer smoke set checks expected
sources, refusal behavior, citation validity, and required terms. Unit tests use fake
embedding, retrieval, reranking, and generation components to avoid external calls.

## Tradeoffs

- Local Qdrant and cross-encoder inference keep the architecture inspectable but add
  startup and operational overhead.
- Hosted Gemini embeddings and generation reduce local model requirements but introduce
  API cost, availability, and data-processing considerations.
- Document-specific chunking produces better metadata than generic fixed windows, at
  the cost of parser maintenance when source layouts change.
- Lightweight validation prevents fabricated citation IDs but cannot establish that
  every statement is entailed by its citation.
