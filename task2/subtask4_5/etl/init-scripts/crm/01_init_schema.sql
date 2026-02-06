-- Схема CRM базы данных

CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    country VARCHAR(100),
    city VARCHAR(100),
    registration_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_prostheses (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    prosthesis_serial_number VARCHAR(50) NOT NULL,
    purchase_date DATE NOT NULL,
    warranty_end_date DATE,
    service_contract_end DATE,
    last_service_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_history (
    id SERIAL PRIMARY KEY,
    client_prosthesis_id INTEGER REFERENCES client_prostheses(id),
    service_date DATE NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    description TEXT,
    cost DECIMAL(10, 2),
    technician VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clients_external_id ON clients(external_id);
CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_client_prostheses_serial ON client_prostheses(prosthesis_serial_number);
CREATE INDEX idx_client_prostheses_client ON client_prostheses(client_id);
