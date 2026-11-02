# Деплой AgroCV

Прод существует с первой недели и дальше только наращивается. Сейчас в проде —
заглушка API (`GET /`, `GET /healthz` и `GET /docs`), задеплоенная из `Dockerfile`.

## Хостинг: Render

Выбран за бесплатный тариф, деплой прямо из GitHub-репозитория и нативную
поддержку Docker: не нужно ничего настраивать под конкретную платформу.

## Как задеплоить (один раз, вручную)

1. Зайти на [render.com](https://render.com) через GitHub-аккаунт.
2. **New** → **Web Service** → подключить публичный репозиторий `vstu-sii/stream-6-agrocv-team`.
3. Настройки сервиса:
   - Runtime: **Docker** — Render возьмёт `Dockerfile` из корня;
   - Branch: `lab1-delivery-initiation` (после merge — `main`);
   - Instance type: **Free**;
   - Health Check Path: `/healthz`;
   - Root Directory: пусто.
4. Environment: `APP_STAGE=prod`, `LOG_LEVEL=INFO`. `MODEL_BASE_URL` и
   `MODEL_API_KEY` добавить, когда появится настоящий модельный шлюз.
5. **Create Web Service** — Render соберёт образ и выдаст публичный URL вида
   `https://<имя-сервиса>.onrender.com`.
6. Проверить: `GET /healthz` должен вернуть `{"status":"ok"}`.
7. Вписать URL в [README.md](../README.md), раздел «Прод», и сюда:

   **Прод-URL:** https://agrocv.onrender.com

## Дальнейшие деплои

Render передеплоивает сервис автоматически при пуше в отслеживаемую ветку
(Auto-Deploy включён по умолчанию). Шаги выше нужны только один раз — при
первом подключении репозитория.

> Сервис создан из ветки `lab1-delivery-initiation` — так нужно, чтобы
> задеплоить до merge PR. После merge: Render Dashboard → сервис → Settings →
> Build & Deploy → переключить Branch на `main`.

## Ограничение бесплатного тарифа

Free тариф Render усыпляет инстанс после простоя, и первый
запрос к «спящему» сервису отвечает долго (десятки секунд). Для заглушки это допустимо; если в
дальнейшем понадобится стабильная латентность — переходить на платный
план или другие варианты.

## Откат

Render Dashboard → Service → Events → выбрать предыдущий успешный деплой →
**Rollback**.

## Прописать адрес на платформе

У платформы Disputa есть метод «адрес стенда своего репозитория: где
развёрнута работа». Адрес сообщается один раз:

```sh
curl -s -X POST -H "Authorization: Bearer $DISPUTA_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"url": "https://<имя-сервиса>.onrender.com"}' \
  "$DISPUTA_URL/api/v1/collaborators/<collaboratorId>/deploy"
```

`<collaboratorId>` — значение `items[].id` из
`GET /api/v1/runs/stream-6/me/repos`. После этого адрес виден в карточке
работы как место, где развёрнута сдача.

## Проверка перед деплоем

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
docker compose -f compose.dev.yml up -d --build
curl -fsS http://127.0.0.1:8000/healthz
docker compose -f compose.dev.yml down
```
