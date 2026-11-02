-- Здесь зафиксировано то, что планируется хранить.
-- Диаграмма ERD: docs/architecture/erd.puml
-- Решение о владельце данных: docs/adr/data-access.md
-- Владелец базы — репозиторий диагнозов (docs/architecture/c4-container.puml),
-- поэтому миграции расположены здесь и применяются им же.

BEGIN;

-- Справочники -------------------------------------------------------------

CREATE TABLE plants (
    id          uuid PRIMARY KEY,
    name_ru     varchar(120) NOT NULL,
    name_latin  varchar(120)
);

CREATE TABLE diseases (
    id          uuid PRIMARY KEY,
    name        varchar(160) NOT NULL,
    kind        varchar(32)  NOT NULL,   -- disease | pest | deficiency
    description text
);

CREATE TABLE drugs (
    id                uuid PRIMARY KEY,
    name              varchar(160) NOT NULL,
    active_substance  varchar(160),
    dosage_min        varchar(80),
    dosage_max        varchar(80),
    waiting_days      int NOT NULL DEFAULT 0,
    source_updated_at timestamptz
);

-- Рабочие данные ---------------------------------------------------------

CREATE TABLE photos (
    id           uuid PRIMARY KEY,
    file_name    varchar(255) NOT NULL,
    content_type varchar(120) NOT NULL,
    size_bytes   int NOT NULL,
    sha256       char(64) NOT NULL,
    uploaded_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE diagnoses (
    id            uuid PRIMARY KEY,
    photo_id      uuid NOT NULL REFERENCES photos (id),
    plant_id      uuid REFERENCES plants (id),
    disease_id    uuid REFERENCES diseases (id),
    confidence    numeric(4, 3),
    source        varchar(16) NOT NULL DEFAULT 'model',  -- model | human
    model_version varchar(64),
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE treatments (
    id           uuid PRIMARY KEY,
    diagnosis_id uuid NOT NULL REFERENCES diagnoses (id),
    drug_id      uuid NOT NULL REFERENCES drugs (id),
    dosage       varchar(80) NOT NULL,
    frequency    varchar(80),
    waiting_days int NOT NULL DEFAULT 0,
    note         text,
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- Журнал ухода: обработку проводят, и отменить её нельзя.
CREATE TABLE journal_entries (
    id           uuid PRIMARY KEY,
    treatment_id uuid NOT NULL REFERENCES treatments (id),
    applied_at   timestamptz NOT NULL DEFAULT now(),
    note         text
);

-- Очередь диагностики: что с фото происходит прямо сейчас.
CREATE TABLE diagnosis_jobs (
    id          uuid PRIMARY KEY,
    photo_id    uuid NOT NULL REFERENCES photos (id),
    status      varchar(16) NOT NULL DEFAULT 'queued',  -- queued | running | done | failed
    error       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);

-- Индексы под типовые выборки -------------------------------------------

CREATE INDEX idx_diagnoses_photo ON diagnoses (photo_id);
CREATE INDEX idx_diagnoses_created ON diagnoses (created_at DESC);
CREATE INDEX idx_treatments_diagnosis ON treatments (diagnosis_id);
CREATE INDEX idx_journal_entries_treatment ON journal_entries (treatment_id);
CREATE INDEX idx_diagnosis_jobs_status ON diagnosis_jobs (status);

COMMIT;
