from fastapi import FastAPI


app = FastAPI(title="BNM Compliance Onboarding Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
