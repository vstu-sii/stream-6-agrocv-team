"""HTTP-сервис AgroCV.

Лаба 1, роль Delivery: каркас приложения с заглушкой. Настоящая логика
диагностики подключается силами роли AI Engineer в следующих лабораторных
работах, поэтому здесь только каркас, который поднимается и отвечает.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import load_settings

settings = load_settings()

app = FastAPI(
    title="AgroCV API",
    version="0.1.0",
    description="Сервис диагностики болезней растений по фото. Лаба 1: каркас и заглушка.",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Проверка живости: контейнер считается готовым, когда этот ответ 200."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, object]:
    """Карточка сервиса: что запущено и куда оно ходит."""
    return {
        "service": settings.app_name,
        "version": app.version,
        "stage": settings.stage,
        "status": "ok",
        "model_gateway": settings.model_base_url,
        "model_configured": settings.model_configured,
    }
