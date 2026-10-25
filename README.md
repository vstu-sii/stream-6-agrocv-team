# AgroCV — диагностика болезней растений по фото

[![CI](https://github.com/vstu-sii/stream-6-agrocv-team/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/vstu-sii/stream-6-agrocv-team/actions/workflows/ci.yml)
[![Статус](https://img.shields.io/badge/status-in_development-yellow)](https://github.com/vstu-sii/stream-6-agrocv-team)
[![Курс](https://img.shields.io/badge/course-SII_2026-blue)](https://sii.sergeivolchkov.ru)

Проект курса «Системы искусственного интеллекта».

## О проекте

В качестве проекта выступает AI-система, которая по фото листа распознаёт вид растения (яблоневых или вишневых культур), ставит диагноз и предлагает конкретное лечение.

## Прод

Публичный URL hello-world: https://agrocv.onrender.com/

Сейчас в проде — заглушка (`GET /`, `GET /healthz`, `GET /docs`), размещённая на Render.com.

## Структура репозитория

```
.
├── .github/
│   └── workflows/
│       └── ci.yml          # lint, format, build — GitHub Actions
├── app/
│   ├── __init__.py
│   ├── config.py           # конфигурация из переменных окружения
│   ├── main.py             # HTTP-сервис: / и /healthz
│   └── stub_gateway.py     # заглушка внешнего сервиса для dev
├── docs/
│   └── deploy.md           # документация по деплою
├── .env.example            # пример переменных окружения (без секретов)
├── .gitignore
├── compose.dev.yml         # dev-окружение: приложение + заглушка
├── Dockerfile              # образ приложения
├── pyproject.toml          # настройки ruff (линт и формат в CI)
├── README.md
└── requirements.txt        # зависимости для сборки образа
```

Структура пополняется по мере работы команды: `docs/prd.md`,
`docs/hypotheses.md`, `docs/glossary.md`, `docs/brief.md` — зона роли
Product; `docs/research.md`, `docs/model-candidates.md`, `docs/experiments/` —
зона роли AI; `docs/quality/`, `evals/`, `tests/` — зона роли Quality.

## Архитектура (текущее состояние)

В dev-окружении поднимаются два контейнера, HTTP между ними (в проде - один (приложение)):

```
клиент ──HTTP──▶ api (FastAPI, :8000) ──HTTP──▶ внешний модельный шлюз
                                  │
                                  └──▶ в dev это stub-gateway (:8080)
```

Пока настоящего модельного шлюза нет, приложение отвечает карточкой сервиса
на `GET /` и проверкой состояния на `GET /healthz`. Логику диагностики
подключает роль AI Engineer; контракт внешнего шлюза — в
`app/stub_gateway.py` (`POST /v1/diagnose`).

## Требования

- Docker 24+ и Docker Compose v2.24+ (в `env_file` используется длинный
  синтаксис с `required: false`)
- Python 3.13+ и `pip` — только если запускаете сервис без Docker
- `ruff==0.17.1` — для линтинга и форматирования

## Установка и запуск (dev)

```bash
git clone https://github.com/vstu-sii/stream-6-agrocv-team.git
cd stream-6-agrocv-team
cp .env.example .env          # значения по умолчанию подходят для dev
docker compose -f compose.dev.yml up -d --build
```

Подъём одной командой занимает меньше 10 минут: собирается образ, из него
запускаются два контейнера.

Что доступно после подъёма:

| Адрес | Описание |
|-------|----------|
| <http://127.0.0.1:8000/> | карточка сервиса |
| <http://127.0.0.1:8000/healthz> | проверка живости |
| <http://127.0.0.1:8000/docs> | Swagger UI |
| <http://127.0.0.1:8080/healthz> | заглушка внешнего сервиса |

Проверка и остановка:

```bash
curl -fsS http://127.0.0.1:8000/healthz
docker compose -f compose.dev.yml ps
docker compose -f compose.dev.yml logs -f
docker compose -f compose.dev.yml down
```

## Локальная разработка без Docker

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Линтинг и форматирование (те же команды, что и в CI):

```bash
pip install "ruff==0.17.1"
ruff check .
ruff format .
ruff format --check .
```

## CI/CD

`.github/workflows/ci.yml` — на каждом PR в `main`:

| Джоб | Что делает |
|------|------------|
| `Lint (ruff check)` | `ruff check .` |
| `Format (ruff format --check)` | `ruff format --check .` |
| `Build (docker image + compose)` | `docker build`, проверка `compose.dev.yml`, smoke-тест контейнера через `/healthz` |

Ветка `main` защищена: без зелёного CI merge не проходит. Статус прогона —
бейдж вверху страницы.

## Команда

| Роль | Основные задачи |
|------|-----------------|
| Product / Vision Owner | Сегмент, гипотезы, use cases, скоуп |
| AI Engineer | Промпты, RAG, качество ответов модели |
| Delivery Engineer | Приложение, compose, CI/CD, прод |
| AI Quality & Safety Engineer | Evals, регрессия, безопасность LLM |

Детальный состав команды доступен внутри курса.

## Документация

- [Deployment Guide](docs/deploy.md)
