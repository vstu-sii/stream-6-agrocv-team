"""HTTP-сервис AgroCV.
Каркас приложения с заглушкой, который поднимается и отвечает.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import load_settings

settings = load_settings()

app = FastAPI(
    title="AgroCV API",
    version="0.1.0",
    description="Сервис диагностики болезней растений по фото.",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": settings.app_name,
        "version": app.version,
        "stage": settings.stage,
        "status": "ok",
        "model_gateway": settings.model_base_url,
        "model_configured": settings.model_configured,
    }
