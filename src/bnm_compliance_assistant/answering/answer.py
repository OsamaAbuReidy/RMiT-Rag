from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import argparse
import json

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from bnm_compliance_assistant.config.settings import settings
from bnm_compliance_assistant.retrieval.bm25 import SearchResult
from bnm_compliance_assistant.retrieval.rerank import RerankedRetriever


SYSTEM_INSTRUCTION = """You are the BNM Compliance Onboarding Assistant.

Answer only from the supplied evidence blocks. Do not use outside knowledge.
Every material claim must cite one or more source_id values from the evidence.
Do not invent clause numbers, page numbers, document names, or citations.
Clearly distinguish Standard (S) obligations from Guidance (G).
If the evidence is insufficient, return refused=true and explain what is missing.
Keep the answer concise, preferably under 150 words.
Return only valid JSON matching this shape:
{
  "answer": "string",
  "refused": false,
  "citations": [{"source_id": "S1"}]
}
"""


class Citation(BaseModel):
    source_id: str
    document: str
    page_number: int
    clause: str | None = None
    tag: str | None = None
    appendix: str | None = None


class Source(BaseModel):
    source_id: str
    id: str
    document: str
    page_number: int
    clause: str | None = None
    tag: str | None = None
    appendix: str | None = None
    score: float
    text: str


class AnswerResponse(BaseModel):
    question: str
    answer: str
    refused: bool
    citations: list[Citation]
    sources: list[Source]


class ModelCitation(BaseModel):
    source_id: str


class ModelAnswer(BaseModel):
    answer: str
    refused: bool = False
    citations: list[ModelCitation] = Field(default_factory=list)


class Retriever(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        ...


class AnswerClient(Protocol):
    def generate(self, question: str, context: str) -> ModelAnswer:
        ...


@dataclass(frozen=True)
class EvidenceContext:
    text: str
    sources: list[Source]


class ContextBuilder:
    def build(self, results: list[SearchResult]) -> EvidenceContext:
        sources = [
            Source(
                source_id=f"S{index}",
                id=result.id,
                document=result.document,
                page_number=result.page_number,
                clause=result.clause,
                tag=result.tag,
                appendix=result.appendix,
                score=result.score,
                text=result.text,
            )
            for index, result in enumerate(results, start=1)
        ]
        blocks = [self._format_block(source) for source in sources]
        return EvidenceContext(text="\n\n".join(blocks), sources=sources)

    def _format_block(self, source: Source) -> str:
        metadata = [
            f"source_id: {source.source_id}",
            f"document: {source.document}",
            f"page_number: {source.page_number}",
        ]
        if source.clause:
            metadata.append(f"clause: {source.clause}")
        if source.tag:
            metadata.append(f"tag: {source.tag}")
        if source.appendix:
            metadata.append(f"appendix: {source.appendix}")
        return "\n".join([f"[{source.source_id}]", *metadata, "text:", source.text])


class GeminiAnswerClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        resolved_api_key = api_key or settings.gemini_api_key
        if not resolved_api_key:
            raise ValueError("GEMINI_API_KEY is required for answer generation")

        self.client = genai.Client(api_key=resolved_api_key)
        self.model = model or settings.gemini_generation_model
        self.max_output_tokens = max_output_tokens or settings.answer_max_output_tokens

    def generate(self, question: str, context: str) -> ModelAnswer:
        prompt = (
            "Question:\n"
            f"{question}\n\n"
            "Evidence:\n"
            f"{context}\n"
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ModelAnswer,
                max_output_tokens=self.max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )
        return ModelAnswer.model_validate_json(response.text or "{}")


@dataclass
class AnswerService:
    retriever: Retriever
    answer_client: AnswerClient
    context_builder: ContextBuilder
    default_top_k: int = 5

    @classmethod
    def from_settings(cls) -> "AnswerService":
        return cls(
            retriever=RerankedRetriever.from_settings(),
            answer_client=GeminiAnswerClient(),
            context_builder=ContextBuilder(),
            default_top_k=settings.answer_top_k,
        )

    def answer(self, question: str, top_k: int | None = None) -> AnswerResponse:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question must not be empty")

        resolved_top_k = top_k or self.default_top_k
        if resolved_top_k < 1:
            raise ValueError("top_k must be at least 1")

        results = self.retriever.search(normalized_question, top_k=resolved_top_k)
        context = self.context_builder.build(results)
        if not context.sources:
            return self._refusal(
                question=normalized_question,
                answer="I do not have enough retrieved context to answer this question.",
                sources=[],
            )

        try:
            model_answer = self.answer_client.generate(normalized_question, context.text)
        except (json.JSONDecodeError, ValueError) as exc:
            return self._refusal(
                question=normalized_question,
                answer=f"The answer model returned an invalid structured response: {exc}",
                sources=context.sources,
            )

        valid_source_ids = {source.source_id for source in context.sources}
        cited_source_ids = [citation.source_id for citation in model_answer.citations]
        if not model_answer.refused and not cited_source_ids:
            return self._refusal(
                question=normalized_question,
                answer="The generated answer did not include citations to the retrieved evidence.",
                sources=context.sources,
            )
        invalid_source_ids = [
            source_id for source_id in cited_source_ids if source_id not in valid_source_ids
        ]
        if invalid_source_ids:
            return self._refusal(
                question=normalized_question,
                answer=(
                    "The generated answer cited sources that were not retrieved: "
                    + ", ".join(invalid_source_ids)
                ),
                sources=context.sources,
            )

        return AnswerResponse(
            question=normalized_question,
            answer=model_answer.answer,
            refused=model_answer.refused,
            citations=self._citations_from_source_ids(cited_source_ids, context.sources),
            sources=context.sources,
        )

    def _citations_from_source_ids(
        self,
        source_ids: list[str],
        sources: list[Source],
    ) -> list[Citation]:
        source_by_id = {source.source_id: source for source in sources}
        citations = []
        for source_id in dict.fromkeys(source_ids):
            source = source_by_id[source_id]
            citations.append(
                Citation(
                    source_id=source.source_id,
                    document=source.document,
                    page_number=source.page_number,
                    clause=source.clause,
                    tag=source.tag,
                    appendix=source.appendix,
                )
            )
        return citations

    def _refusal(self, question: str, answer: str, sources: list[Source]) -> AnswerResponse:
        return AnswerResponse(
            question=question,
            answer=answer,
            refused=True,
            citations=[],
            sources=sources,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Answer a BNM compliance question with citations.")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("--top-k", type=int, default=settings.answer_top_k, help="Retrieved sources to use")
    args = parser.parse_args()

    service = AnswerService.from_settings()
    response = service.answer(args.question, top_k=args.top_k)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
