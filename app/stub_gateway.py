"""Заглушка внешнего сервиса."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="AgroCV stub gateway", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/diagnose")
def diagnose(payload: dict[str, object]) -> dict[str, object]:
    """Здесь будет вызов модели."""
    return {
        "stub": True,
        "message": "Заглушка: настоящий модельный шлюз подключается силами роли AI Engineer.",
        "received": payload,
    }
