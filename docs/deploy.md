# Деплой AgroCV

Лаба 1, роль Delivery: «Hello-world в прод» — приложение должно быть доступно
по публичному URL, который открывается у любого члена команды.

Стенд курса как площадку не используем: он нужен под полноценный прод в
следующих лабораторных работах. Ниже — варианты с Docker.

## Что деплоим

| Что | Значение |
|-----|----------|
| Образ | `agrocv-api`, собирается из `Dockerfile` в корне репозитория |
| Команда запуска | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (`$PORT` задаёт хостинг) |
| Проверка живости | `GET /healthz` → `{"status":"ok"}` |
| Секреты | `MODEL_API_KEY` и прочие — в переменных окружения хостинга |

Тот же образ собирается и в CI, и в compose, и на хостинге — одна и та же
сборка проверяется до сдачи.

## Вариант 1 — Render (рекомендуемый)

Docker-образ прямо из репозитория, без реестра образов и без CLI на сервере.

1. Аккаунт на [render.com](https://render.com), вход через GitHub под
   `TestMaster-AI`.
2. **New → Web Service → Connect repo** → `vstu-sii/stream-6-agrocv-team`.
3. Ветка: `main` (после мержа своей ветки) либо `lab1-delivery-initiation`.
4. **Runtime: Docker** — Render возьмёт `Dockerfile` из корня сам.
   Region: ближайший к России (Frankfurt / Singapore), Instance type: **Free**.
5. **Health Check Path**: `/healthz`.
6. **Environment**: `APP_STAGE=prod`, `LOG_LEVEL=INFO`,
   `MODEL_BASE_URL=<адрес модельного шлюза>`, `MODEL_API_KEY=<ключ>`.
7. **Create Web Service** → сборка образа (2–4 минуты) → публичный адрес
   `https://<имя-сервиса>.onrender.com`.
8. Проверка:

   ```bash
   curl -fsS https://<имя-сервиса>.onrender.com/healthz
   curl -fsS https://<имя-сервиса>.onrender.com/
   ```

9. Дальше любой `push` в выбранную ветку пересобирает и передеплоит сервис
   сам.

## Вариант 2 — Koyeb

Устроено так же: **New Service → Docker** (из репозитория или из своего
registry), порт `8000`, health check `/healthz`, адрес вида
`https://<приложение>-<регион>.koyeb.app`. Автодеплой по push работает
аналогично.

## Вариант 3 — Yandex Cloud Containers

Если у команды есть аккаунт Yandex Cloud. Образ нужно положить в Container
Registry, контейнер — поднять в Serverless Containers:

```bash
# 1. сборка и загрузка образа в свой registry
docker build -t cr.yandex.ru/crXXXXXX/agrocv-api:latest .
docker login -u iam-user cr.yandex.ru/crXXXXXX
docker push cr.yandex.ru/crXXXXXX/agrocv-api:latest

# 2. контейнер и его запуск
yc serverless container create \
  --name agrocv-api \
  --image cr.yandex.ru/crXXXXXX/agrocv-api:latest \
  --port 8000 \
  --platform managed \
  --memory 256M \
  --cpu 0.25
yc serverless container deploy agrocv-api

# 3. публичный адрес
yc serverless container get agrocv-api --format json   # gatewayUrl / url
curl -fsS https://<адрес>/healthz
```

Оговорки: нужен активированный платёжный профиль (даже под тестовые лимиты),
а контейнер масштабируется в ноль при простое — либо держать минимальное число
инстансов, либо пинговать (см. следующий раздел).

## Как не дать бесплатному инстансу заснуть

Бесплатные тарифы Render и Koyeb усыпляют инстанс после простоя, и первый
запрос к «спящему» сервису отвечает долго (десятки секунд). Чтобы проверяющий
получал быстрый ответ, в репозитории есть пинг:

`.github/workflows/keepalive.yml` — раз в 10 минут дёргает `DEPLOY_URL`.

Адрес задаётся один раз в GitHub: **Settings → Secrets and variables →
Actions → Variables → New variable** → имя `DEPLOY_URL`, значение
`https://<публичный-url>`. Пока переменная не задана, workflow ничего не
делает.

## Как сообщить платформе адрес

У платформы Disputa есть метод «адрес стенда своего репозитория: где
развёрнута работа»:

```sh
curl -s -X POST -H "Authorization: Bearer $DISPUTA_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"url": "https://<публичный-url>"}' \
  "$DISPUTA_URL/api/v1/collaborators/<collaboratorId>/deploy"
```

`<collaboratorId>` — значение `items[].id` из
`GET /api/v1/runs/stream-6/me/repos`. После этого адрес виден в карточке
работы как место, где развёрнута сдача.

Параллельно URL вписывается в `README.md`, раздел «Прод» — это проверяют и
человек, и агент-проверяющий.

## Как обновлять

Правка в ветке, которая настроена в хостинге → автодеплой → сервис отвечает
новой версией. Откат — revert-коммит и ещё один автодеплой.

Для своего сервера (если появится) деплой выглядит так:

```bash
docker build -t agrocv-api:prod .
docker run -d --name agrocv-api --restart always \
  --env-file .env -p 8000:8000 agrocv-api:prod
```

## Секреты

`MODEL_API_KEY` и прочие ключи живут в переменных окружения хостинга
(Render/Koyeb — Environment, Yandex — `--env`/секреты) или в `.env` на
сервере с правами `0600`. В репозитории — только `.env.example` без значений.

## Проверка перед сдачей

```bash
curl -fsS https://<публичный-url>/healthz   # {"status":"ok"}
curl -fsS https://<публичный-url>/          # карточка сервиса
```

Оба ответа должны приходить извне команды — с чужой сети и без VPN вуза.
