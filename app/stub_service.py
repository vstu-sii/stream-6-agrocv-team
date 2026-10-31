"""Заглушка сервиса."""

from __future__ import annotations

import os

from fastapi import FastAPI

SERVICE_NAME = os.getenv("SERVICE_NAME", "stub")
SERVICE_KIND = os.getenv("SERVICE_KIND", "заглушка сервиса")

app = FastAPI(title=f"AgroCV {SERVICE_NAME}", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST"])
def stub(path: str) -> dict[str, object]:
    """Любой запрос: фиксированный ответ с именем заглушки."""
    return {
        "service": SERVICE_NAME,
        "kind": SERVICE_KIND,
        "stub": True,
        "path": f"/{path}",
    }
