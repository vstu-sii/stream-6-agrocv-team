# Основания проектирования

Материалы курса прочитаны 31.10.2026. Они определяют форму артефактов; не подтверждают качество нашей модели или состоявшуюся проверку с человеком.

| Источник | Применение |
| --- | --- |
| [Лаба 2](https://sii.sergeivolchkov.ru/labs/lab2) | Четыре результата PRODUCT / VO, роли команды и DoD |
| [Use cases](https://sii.sergeivolchkov.ru/materials/use-cases/writing) | Цель актёра, альтернативы, измеримые критерии и внешний прогон |
| [UML use-case диаграмма](https://sii.sergeivolchkov.ru/materials/use-cases/uml) | Граница системы, актёры, направление extend, совпадение диаграммы и текстов |
| [C4 и ADR](https://sii.sergeivolchkov.ru/materials/architecture/c4-levels) | Структурные решения, альтернативы, цена и проверка |
| [Абстракции](https://sii.sergeivolchkov.ru/materials/architecture/abstractions) | Простая граница распознавания без недоказанного набора сервисов |
| [aact](https://sii.sergeivolchkov.ru/materials/architecture/aact) | Проверка фактической архитектуры и обоснование правил; относится к работе с C4 команды |
| [Evals](https://sii.sergeivolchkov.ru/materials/quality/evals) | Связь критериев UC с контрольными примерами, baseline и регрессией |
| [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) | Официальная карточка выбранной мультимодальной модели; вход изображение + текст, генерация ответа |
| [PlantUML CLI](https://plantuml.com/command-line) | Проверка и генерация SVG из исходника диаграммы |

Предметный охват и целевые метрики продолжают первую лабораторную: только яблони, четыре класса, существующие модели с дообучением на открытых данных при необходимости. Числовые пределы и принятый для проектирования вариант хранения/размещения требуют технической проверки.

Для Qwen3-VL применяются требования к генеративной модели: версия промпта, проверка структурированного ответа, учёт токенов, задержки и ошибок. Качество оценивается по независимым меткам изображений. Свободный чат и RAG не входят в MVP.


- [Docker: основы](https://sii.sergeivolchkov.ru/materials/docker/basics) — упаковка серверного приложения.
- [Docker Compose](https://sii.sergeivolchkov.ru/materials/docker/compose) — воспроизводимый совместный запуск.
- [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) — выбранная модель; порядок интеграции описан в model-usage.md.

[Диаграмма в PlantUML Online](https://www.plantuml.com/plantuml/uml/ZLFDRjD04BxxAOPmWOEZDab_LAfAJL1E20b5vK9wM99DQZNPhTORXOAGyYErI21LGfn10Xx0IMiQsYPzXTatOjPkKgUaWfl7yyttCnu_E52itcJGO8UofS5lSiq4Sngyfa5BK5vzJqFLKxoYFIaSVzyJ1qon9lXxh2hRdgX3ZJLydkXKUOsr6heeXNxEcXnAJFWbhhpQOap9UyjXEPTe7h3AFglpaZviSB3AJDGRIOLjfMIx81jImSFS-khIQZ7HP1KjLLwgAbSta4mkjxvII41QFgymd-T9fwvaIrHlWCLCSQsulG2OP5l9hAskvnEWcSD5ejhJ50A_u0W3FCKnJapNzAYwm01mW1Eyn13FgH7YRw1YPFlc4vL3C2U4k2JC64UE4mM357wcLm6U4O96pT4SAWNC1zaMN3apMz58Y0FNT6DsAgwi-ja2KwEoU8G3qy70zCbMQ3g08w19Ui9XN0_XgQpiS_Ku1UySc2u9KZi5Tsav3VZDfZ9zSqno50NmccP3aXiIQyU-jDufuzXyfD1Hyvpaw1Mr0jCh2xp6oUqs-dCPoy9r2V6TN1zRnn2vxPeFXBPK134d6sL1WxOS47D8prrp0cIg5usDOno61FjB7gow_K2qW037qKvt2alBTxDcAEkF6M6SzVumj6LQm0IlR9nkf7w55wO_fS_SfSyI_LTpT9CeNcJYNYRneInGn63AcNNUEqvq3k2wSOPabPchievz1UdqLeI43TZSv6yq5zMjhR9uzL_htBKSsViv_hNhNSSHKdDuBRMMJP2rwU9VjBd8kY-VkRay7I3TJRoACHt6r0qv2EOk5SFRMqqJ1_uaiptxBQpMgUcGaL_qD8jp74_XESp_0a_cVm3Rih-kJM27aogK56o2Fm00). Исходник, SVG и PNG входят в пакет.
