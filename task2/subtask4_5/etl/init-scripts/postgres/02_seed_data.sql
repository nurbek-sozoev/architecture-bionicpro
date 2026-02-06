-- Тестовые данные для основной базы (телеметрия)

INSERT INTO prostheses (serial_number, model, firmware_version, production_date) VALUES
    ('BP-2025-001', 'BionicHand Pro X1', '3.2.1', '2025-03-15'),
    ('BP-2025-002', 'BionicHand Pro X1', '3.2.1', '2025-04-20'),
    ('BP-2025-003', 'BionicHand Lite L1', '2.5.0', '2025-05-10'),
    ('BP-2025-004', 'BionicHand Pro X2', '3.3.0', '2025-06-05'),
    ('BP-2025-005', 'BionicHand Pro X2', '3.3.0', '2025-07-12'),
    ('BP-2025-006', 'BionicHand Lite L1', '2.5.1', '2025-08-01'),
    ('BP-2025-007', 'BionicArm Elite E1', '4.0.0', '2025-09-15'),
    ('BP-2025-008', 'BionicHand Pro X1', '3.2.2', '2025-10-01'),
    ('BP-2025-009', 'BionicArm Elite E1', '4.0.1', '2025-11-20'),
    ('BP-2025-010', 'BionicHand Pro X2', '3.3.1', '2025-12-01');

-- Генерация телеметрии за последние 30 дней
DO $$
DECLARE
    prosthesis_rec RECORD;
    current_date_val DATE;
    hour_val INTEGER;
    battery DECIMAL;
    response_time INTEGER;
    grip DECIMAL;
    myosignal DECIMAL;
    movements INTEGER;
    temp DECIMAL;
    err_code VARCHAR(10);
BEGIN
    FOR prosthesis_rec IN SELECT id FROM prostheses LOOP
        FOR day_offset IN 0..29 LOOP
            current_date_val := CURRENT_DATE - day_offset;
            FOR hour_val IN 8..20 LOOP
                battery := 20 + RANDOM() * 80;
                response_time := 15 + FLOOR(RANDOM() * 45)::INTEGER;
                grip := 30 + RANDOM() * 70;
                myosignal := 0.1 + RANDOM() * 2.5;
                movements := 50 + FLOOR(RANDOM() * 200)::INTEGER;
                temp := 30 + RANDOM() * 8;
                
                IF RANDOM() < 0.02 THEN
                    err_code := 'E' || LPAD((FLOOR(RANDOM() * 100)::INTEGER)::TEXT, 3, '0');
                ELSE
                    err_code := NULL;
                END IF;

                INSERT INTO telemetry (
                    prosthesis_id,
                    recorded_at,
                    battery_level,
                    response_time_ms,
                    grip_strength,
                    myosignal_amplitude,
                    movements_count,
                    temperature,
                    error_code
                ) VALUES (
                    prosthesis_rec.id,
                    current_date_val + (hour_val || ' hours')::INTERVAL + (FLOOR(RANDOM() * 59)::INTEGER || ' minutes')::INTERVAL,
                    battery,
                    response_time,
                    grip,
                    myosignal,
                    movements,
                    temp,
                    err_code
                );
            END LOOP;
        END LOOP;
    END LOOP;
END $$;
