CREATE TABLE external_raw_records (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(80) NOT NULL,
    external_id VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_external_raw_source_id UNIQUE (source_system, external_id)
);

CREATE TABLE dwh_external_record_facts (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(80) NOT NULL,
    external_id VARCHAR(120) NOT NULL,
    name VARCHAR(200),
    status VARCHAR(60),
    amount NUMERIC(12, 2),
    occurred_at TIMESTAMPTZ,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dwh_external_fact_source_id UNIQUE (source_system, external_id)
);
