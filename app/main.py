"""Computer Shop API entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="Computer Shop API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
