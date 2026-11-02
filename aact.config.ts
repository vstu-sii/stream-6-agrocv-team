import type { AactConfig } from "aact";

const config: AactConfig = {
  source: {
    type: "plantuml",
    path: "./docs/architecture/c4-container.puml",
  },

  rules: {
    // Нарушение только из acl-адаптеров во внешние системы: у нас их два
    // (модельный провайдер и справочник препаратов), оба помечены $tags="acl".
    acl: true,

    // Циклов в графе зависимостей нет: web → api → queue ← ai_worker → адаптеры.
    acyclic: true,

    // Внешние REST-вызовы идут через API Gateway: в технологии ребра
    // адаптеров указано "HTTPS via API Gateway".
    apiGateway: true,

    // К базе ходит только владелец данных: репозиторий диагнозов ($tags="repo").
    crud: true,

    // У каждой базы один владелец: diagnostics_db принадлежит diagnostics_repo.
    dbPerService: true,

    // Внутренних связей больше, чем внешних: 7 внутри контейнера против
    // 3 наружу (два внешних сервиса и два человека).
    cohesion: true,

    // Выключено: компоненты не размечены по стабильности, правило считает
    // нестабильность по структуре графа и ругается на «фронтенд зависит от
    // бэкенда». Размечать стабильность будем после ADR о зрелости модулей
    // (лаба 3), тогда правило включаем.
    stableDependencies: false,

    // Потребители контекста используют его публичный API целиком.
    commonReuse: true,
  },
};

export default config;
