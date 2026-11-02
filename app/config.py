"""Конфигурация сервиса."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str
    stage: str
    log_level: str
    host: str
    port: int
    model_base_url: str
    model_api_key: str

    @property
    def model_configured(self) -> bool:
        return bool(self.model_api_key)


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "agrocv-api"),
        stage=os.getenv("APP_STAGE", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        model_base_url=os.getenv("MODEL_BASE_URL", "http://stub-gateway:8080"),
        model_api_key=os.getenv("MODEL_API_KEY", ""),
    )
