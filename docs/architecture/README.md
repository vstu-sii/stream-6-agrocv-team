# Архитектура AgroCV

Диаграммы ведём как код в PlantUML. Файлы `.puml` — источники истины;
SVG в `rendered/` собраны из этих исходников и удобны для просмотра.

| Диаграмма | Исходник | Рендер |
|---|---|---|
| C4 Level 1 — системный контекст | [c4-context.puml](c4-context.puml) | [rendered/c4-context.svg](rendered/c4-context.svg) |
| C4 Level 2 — контейнеры | [c4-container.puml](c4-container.puml) | [rendered/c4-container.svg](rendered/c4-container.svg) |
| ERD | [../../database/erd.puml](../../database/erd.puml) | пока не генерируется в репозитории |

Контекст показывает пользователей, AgroCV как систему и внешние интеграции.
Диаграмма контейнеров раскрывает исполняемые части системы, хранилище и связи
между ними. Внутренние контейнеры — проектная модель; dev-окружение пока
поднимает заглушки, а не реализует все эти сервисы.

## Проверки

Правила aact применяются к [диаграмме контейнеров](c4-container.puml) через
`aact.config.ts` в корне репозитория:

```powershell
npx --yes aact@beta check
```

Для локального рендеринга из корня репозитория нужен Docker Desktop:

```powershell
$repoPath = (Get-Location).Path
docker run --rm -v "${repoPath}:/data" plantuml/plantuml -charset UTF-8 -tsvg -o rendered /data/docs/architecture/c4-context.puml /data/docs/architecture/c4-container.puml
```

Команда использует C4 PlantUML из стандартной библиотеки образа и записывает
результаты в `docs/architecture/rendered/`.
