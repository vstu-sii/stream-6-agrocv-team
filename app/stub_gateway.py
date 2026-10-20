"""Заглушка внешнего сервиса (модельный шлюз).

Нужна, чтобы dev-окружение поднималось одной командой без ключей и без
доступа в интернет: вместо настоящей модели отвечает этот сервис.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="AgroCV stub gateway", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Проверка живости заглушки."""
    return {"status": "ok"}


@app.post("/v1/diagnose")
def diagnose(payload: dict[str, object]) -> dict[str, object]:
    """Фиксированный ответ вместо вызова модели."""
    return {
        "stub": True,
        "message": "Заглушка: настоящий модельный шлюз подключается силами роли AI Engineer.",
        "received": payload,
    }
