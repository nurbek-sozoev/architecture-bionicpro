-- Схема основной базы данных BionicPRO (телеметрия)

CREATE TABLE IF NOT EXISTS prostheses (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    firmware_version VARCHAR(20),
    production_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    prosthesis_id INTEGER REFERENCES prostheses(id),
    recorded_at TIMESTAMP NOT NULL,
    battery_level DECIMAL(5, 2),
    response_time_ms INTEGER,
    grip_strength DECIMAL(5, 2),
    myosignal_amplitude DECIMAL(8, 4),
    movements_count INTEGER,
    temperature DECIMAL(4, 1),
    error_code VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telemetry_prosthesis_id ON telemetry(prosthesis_id);
CREATE INDEX idx_telemetry_recorded_at ON telemetry(recorded_at);
CREATE INDEX idx_telemetry_composite ON telemetry(prosthesis_id, recorded_at);
