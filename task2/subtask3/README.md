# Задание 2. Архитектура системы отчетов BionicPRO

## Задача 3. API для отчетов BionicPRO

## Описание

Бэкенд-приложение с API `/reports` для получения отчетов по клиентам из OLAP-хранилища ClickHouse. API работает с предварительно подготовленными витринами данных, что исключает необходимость выполнения сложных вычислений в реальном времени.

## API Endpoints

### GET /reports/clients

Получить список всех клиентов с агрегированной статистикой.

**Query параметры:**

- `limit` (int, default=100): количество записей
- `offset` (int, default=0): смещение

**Пример ответа:**

```json
{
  "clients": [
    {
      "client_id": 1,
      "client_external_id": "CL001",
      "client_name": "Иван Петров",
      "client_email": "ivan@example.com",
      "client_city": "Москва",
      "client_country": "Russia",
      "registration_date": "2023-01-15",
      "total_prostheses": 1,
      "active_prostheses": 1,
      "avg_daily_movements": 1250.5,
      "avg_battery_level": 75.3,
      "avg_response_time_ms": 12.5,
      "total_errors_30d": 2,
      "last_activity_date": "2024-01-20",
      "days_since_last_service": 45
    }
  ],
  "total": 10
}
```

### GET /reports/client/{client_id}

Получить детальный отчёт по конкретному клиенту, включая историю телеметрии.

**Path параметры:**

- `client_id` (int): ID клиента

**Query параметры:**

- `days` (int, default=30): количество дней истории

**Пример ответа:**

```json
{
  "summary": {
    "client_id": 1,
    "client_name": "Иван Петров",
    "total_prostheses": 1,
    "avg_daily_movements": 1250.5,
    "...": "..."
  },
  "telemetry_history": [
    {
      "report_date": "2024-01-20",
      "client_id": 1,
      "client_name": "Иван Петров",
      "prosthesis_serial_number": "BP-2023-001",
      "prosthesis_model": "BionicHand Pro",
      "avg_battery_level": 78.5,
      "min_battery_level": 65.0,
      "max_battery_level": 95.0,
      "avg_response_time_ms": 11.2,
      "total_movements_count": 1300,
      "error_count": 0,
      "...": "..."
    }
  ]
}
```

### GET /reports/prosthesis/{serial_number}

Получить отчёт по конкретному протезу.

**Path параметры:**

- `serial_number` (string): серийный номер протеза

**Query параметры:**

- `days` (int, default=30): количество дней истории

## Запуск

### Запуск всех сервисов (ETL + API)

```bash
cd task2/subtask3
docker-compose up -d --build
```

### Доступ к интерфейсам

- **Reports API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **Airflow UI:** http://localhost:8080 (admin/admin)
- **ClickHouse:** http://localhost:8124

## Примеры запросов

### Получить список всех клиентов

```bash
curl http://localhost:8000/reports/clients
```

### Получить отчёт по клиенту

```bash
curl http://localhost:8000/reports/client/1?days=30
```

### Получить отчёт по протезу

```bash
curl "http://localhost:8000/reports/prosthesis/BP-2024-001?days=7"
```

## Витрины данных

API использует следующие предварительно подготовленные витрины в ClickHouse:

### dm_client_summary

Сводная статистика по клиентам (обновляется ежедневно ETL):

- Общее количество протезов
- Средние показатели за 30 дней
- Количество ошибок
- Дата последней активности

### dm_client_telemetry_daily

Ежедневная агрегация телеметрии:

- Средние/мин/макс значения метрик за день
- Количество движений
- Количество ошибок

## Остановка

```bash
cd task2/subtask3
docker-compose down
```

Для полной очистки (включая данные):

```bash
docker-compose down -v
```
