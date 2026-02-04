-- Схема аналитической базы ClickHouse

CREATE DATABASE IF NOT EXISTS analytics;

-- Таблица метаданных ETL для отслеживания обработанных периодов
CREATE TABLE IF NOT EXISTS analytics.etl_metadata
(
    dag_id String,
    last_processed_date Date,
    records_processed Int64 DEFAULT 0,
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY dag_id;

-- Staging таблица для данных CRM
CREATE TABLE IF NOT EXISTS analytics.stg_crm_clients
(
    client_id Int32,
    external_id String,
    first_name String,
    last_name String,
    email String,
    phone String,
    country String,
    city String,
    registration_date Date,
    status String,
    prosthesis_serial_number String,
    purchase_date Date,
    warranty_end_date Nullable(Date),
    service_contract_end Nullable(Date),
    last_service_date Nullable(Date),
    prosthesis_status String,
    loaded_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (client_id, prosthesis_serial_number)
PARTITION BY toYYYYMM(purchase_date);

-- Staging таблица для телеметрии
CREATE TABLE IF NOT EXISTS analytics.stg_telemetry
(
    telemetry_id Int32,
    prosthesis_serial_number String,
    prosthesis_model String,
    recorded_at DateTime,
    battery_level Decimal(5, 2),
    response_time_ms Int32,
    grip_strength Decimal(5, 2),
    myosignal_amplitude Decimal(8, 4),
    movements_count Int32,
    temperature Decimal(4, 1),
    error_code Nullable(String),
    loaded_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (prosthesis_serial_number, recorded_at)
PARTITION BY toYYYYMM(recorded_at);

-- Витрина: агрегированные данные телеметрии в разрезе клиентов
CREATE TABLE IF NOT EXISTS analytics.dm_client_telemetry_daily
(
    report_date Date,
    client_id Int32,
    client_external_id String,
    client_name String,
    client_city String,
    client_country String,
    prosthesis_serial_number String,
    prosthesis_model String,
    
    -- Агрегированные метрики телеметрии за день
    avg_battery_level Decimal(5, 2),
    min_battery_level Decimal(5, 2),
    max_battery_level Decimal(5, 2),
    
    avg_response_time_ms Decimal(8, 2),
    min_response_time_ms Int32,
    max_response_time_ms Int32,
    
    avg_grip_strength Decimal(5, 2),
    avg_myosignal_amplitude Decimal(8, 4),
    
    total_movements_count Int32,
    avg_temperature Decimal(4, 1),
    
    error_count Int32,
    records_count Int32,
    
    -- Сервисная информация
    warranty_end_date Nullable(Date),
    service_contract_end Nullable(Date),
    last_service_date Nullable(Date),
    
    loaded_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (client_id, prosthesis_serial_number, report_date)
PARTITION BY toYYYYMM(report_date);

-- Витрина: сводная статистика по клиентам
CREATE TABLE IF NOT EXISTS analytics.dm_client_summary
(
    client_id Int32,
    client_external_id String,
    client_name String,
    client_email String,
    client_city String,
    client_country String,
    registration_date Date,
    
    total_prostheses Int32,
    active_prostheses Int32,
    
    -- Агрегированные метрики по всем протезам клиента
    avg_daily_movements Decimal(10, 2),
    avg_battery_level Decimal(5, 2),
    avg_response_time_ms Decimal(8, 2),
    total_errors_30d Int32,
    
    last_activity_date Nullable(Date),
    days_since_last_service Nullable(Int32),
    
    loaded_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(loaded_at)
ORDER BY (client_id)
PARTITION BY toYYYYMM(registration_date);
