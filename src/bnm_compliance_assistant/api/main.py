from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bnm_compliance_assistant.answering.answer import AnswerResponse, AnswerService
from bnm_compliance_assistant.config.settings import settings


app = FastAPI(title="BNM Compliance Onboarding Assistant")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1)


def get_answer_service() -> AnswerService:
    return AnswerService.from_settings()


@app.post("/answer", response_model=AnswerResponse)
def answer(
    request: AnswerRequest,
    service: AnswerService = Depends(get_answer_service),
) -> AnswerResponse:
    try:
        return service.answer(
            request.question,
            top_k=request.top_k or settings.answer_top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
