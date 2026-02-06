from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from utils.clickhouse_client import insert_clickhouse_data, execute_clickhouse_query


default_args = {
    'owner': 'bionicpro-etl',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def extract_crm_clients(**context):
    pg_hook = PostgresHook(postgres_conn_id='postgres_crm')
    
    query = """
        SELECT 
            c.id as client_id,
            c.external_id,
            c.first_name,
            c.last_name,
            c.email,
            c.phone,
            c.country,
            c.city,
            c.registration_date,
            c.status,
            cp.prosthesis_serial_number,
            cp.purchase_date,
            cp.warranty_end_date,
            cp.service_contract_end,
            cp.last_service_date,
            cp.status as prosthesis_status
        FROM clients c
        INNER JOIN client_prostheses cp ON c.id = cp.client_id
        WHERE c.status = 'active'
    """
    
    records = pg_hook.get_records(query)
    
    if records:
        columns = [
            'client_id', 'external_id', 'first_name', 'last_name', 
            'email', 'phone', 'country', 'city', 'registration_date', 
            'status', 'prosthesis_serial_number', 'purchase_date',
            'warranty_end_date', 'service_contract_end', 'last_service_date',
            'prosthesis_status'
        ]
        insert_clickhouse_data('analytics.stg_crm_clients', records, columns)
    
    print(f"Extracted and loaded {len(records)} CRM records")
    return len(records)


def extract_telemetry(**context):
    execution_date = context['execution_date']
    date_from = execution_date - timedelta(days=30)
    date_to = execution_date + timedelta(days=1)
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_main')
    
    query = """
        SELECT 
            t.id as telemetry_id,
            p.serial_number as prosthesis_serial_number,
            p.model as prosthesis_model,
            t.recorded_at,
            t.battery_level,
            t.response_time_ms,
            t.grip_strength,
            t.myosignal_amplitude,
            t.movements_count,
            t.temperature,
            t.error_code
        FROM telemetry t
        INNER JOIN prostheses p ON t.prosthesis_id = p.id
        WHERE t.recorded_at >= %s AND t.recorded_at < %s
        ORDER BY t.recorded_at
    """
    
    records = pg_hook.get_records(query, parameters=[date_from, date_to])
    
    if records:
        columns = [
            'telemetry_id', 'prosthesis_serial_number', 'prosthesis_model',
            'recorded_at', 'battery_level', 'response_time_ms', 'grip_strength',
            'myosignal_amplitude', 'movements_count', 'temperature', 'error_code'
        ]
        insert_clickhouse_data('analytics.stg_telemetry', records, columns)
    
    print(f"Extracted and loaded {len(records)} telemetry records")
    return len(records)


def build_daily_marts(**context):
    execution_date = context['execution_date']
    
    for day_offset in range(30):
        report_date = (execution_date - timedelta(days=day_offset)).strftime('%Y-%m-%d')
        
        query = """
            INSERT INTO analytics.dm_client_telemetry_daily (
                report_date,
                client_id,
                client_external_id,
                client_name,
                client_city,
                client_country,
                prosthesis_serial_number,
                prosthesis_model,
                avg_battery_level,
                min_battery_level,
                max_battery_level,
                avg_response_time_ms,
                min_response_time_ms,
                max_response_time_ms,
                avg_grip_strength,
                avg_myosignal_amplitude,
                total_movements_count,
                avg_temperature,
                error_count,
                records_count,
                warranty_end_date,
                service_contract_end,
                last_service_date
            )
            SELECT 
                toDate(%(report_date)s) as report_date,
                c.client_id,
                c.external_id as client_external_id,
                concat(c.first_name, ' ', c.last_name) as client_name,
                c.city as client_city,
                c.country as client_country,
                t.prosthesis_serial_number,
                any(t.prosthesis_model) as prosthesis_model,
                
                round(avg(t.battery_level), 2) as avg_battery_level,
                min(t.battery_level) as min_battery_level,
                max(t.battery_level) as max_battery_level,
                
                round(avg(t.response_time_ms), 2) as avg_response_time_ms,
                min(t.response_time_ms) as min_response_time_ms,
                max(t.response_time_ms) as max_response_time_ms,
                
                round(avg(t.grip_strength), 2) as avg_grip_strength,
                round(avg(t.myosignal_amplitude), 4) as avg_myosignal_amplitude,
                
                sum(t.movements_count) as total_movements_count,
                round(avg(t.temperature), 1) as avg_temperature,
                
                countIf(t.error_code IS NOT NULL AND t.error_code != '') as error_count,
                count() as records_count,
                
                any(c.warranty_end_date) as warranty_end_date,
                any(c.service_contract_end) as service_contract_end,
                any(c.last_service_date) as last_service_date
                
            FROM analytics.stg_telemetry t
            INNER JOIN analytics.stg_crm_clients c 
                ON t.prosthesis_serial_number = c.prosthesis_serial_number
            WHERE toDate(t.recorded_at) = toDate(%(report_date)s)
            GROUP BY 
                c.client_id,
                c.external_id,
                c.first_name,
                c.last_name,
                c.city,
                c.country,
                t.prosthesis_serial_number
            HAVING count() > 0
        """
        
        execute_clickhouse_query(query, {'report_date': report_date})
    
    print("Built daily marts for last 30 days")
    return "Daily marts built"


def build_client_summary(**context):
    query = """
        INSERT INTO analytics.dm_client_summary (
            client_id,
            client_external_id,
            client_name,
            client_email,
            client_city,
            client_country,
            registration_date,
            total_prostheses,
            active_prostheses,
            avg_daily_movements,
            avg_battery_level,
            avg_response_time_ms,
            total_errors_30d,
            last_activity_date,
            days_since_last_service
        )
        SELECT 
            c.client_id,
            c.external_id as client_external_id,
            concat(c.first_name, ' ', c.last_name) as client_name,
            any(c.email) as client_email,
            any(c.city) as client_city,
            any(c.country) as client_country,
            any(c.registration_date) as registration_date,
            
            count(DISTINCT c.prosthesis_serial_number) as total_prostheses,
            countIf(c.prosthesis_status = 'active') as active_prostheses,
            
            round(avgIf(dt.total_movements_count, dt.report_date >= today() - 30), 2) as avg_daily_movements,
            round(avgIf(dt.avg_battery_level, dt.report_date >= today() - 30), 2) as avg_battery_level,
            round(avgIf(dt.avg_response_time_ms, dt.report_date >= today() - 30), 2) as avg_response_time_ms,
            sumIf(dt.error_count, dt.report_date >= today() - 30) as total_errors_30d,
            
            maxIf(dt.report_date, dt.records_count > 0) as last_activity_date,
            
            if(
                max(c.last_service_date) IS NOT NULL,
                toInt32(dateDiff('day', max(c.last_service_date), today())),
                NULL
            ) as days_since_last_service
            
        FROM analytics.stg_crm_clients c
        LEFT JOIN analytics.dm_client_telemetry_daily dt 
            ON c.client_id = dt.client_id 
            AND c.prosthesis_serial_number = dt.prosthesis_serial_number
        GROUP BY 
            c.client_id,
            c.external_id,
            c.first_name,
            c.last_name
    """
    
    execute_clickhouse_query(query)
    print("Built client summary mart")
    return "Client summary built"


def verify_and_report(**context):
    queries = {
        'CRM staging': "SELECT count() FROM analytics.stg_crm_clients",
        'Telemetry staging': "SELECT count() FROM analytics.stg_telemetry",
        'Daily mart': "SELECT count() FROM analytics.dm_client_telemetry_daily",
        'Summary mart': "SELECT count() FROM analytics.dm_client_summary",
    }
    
    results = {}
    for name, query in queries.items():
        result = execute_clickhouse_query(query)
        count = result[0][0] if result else 0
        results[name] = count
        print(f"{name}: {count} records")
    
    return results


def optimize_tables(**context):
    tables = [
        'analytics.stg_crm_clients',
        'analytics.stg_telemetry',
        'analytics.dm_client_telemetry_daily',
        'analytics.dm_client_summary'
    ]
    
    for table in tables:
        execute_clickhouse_query(f"OPTIMIZE TABLE {table} FINAL")
        print(f"Optimized {table}")
    
    return "Tables optimized"


with DAG(
    'bionicpro_etl_full',
    default_args=default_args,
    description='Full BionicPRO ETL pipeline - extracts, transforms and loads all data',
    schedule_interval='0 3 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'full', 'bionicpro'],
) as dag:
    
    extract_crm_task = PythonOperator(
        task_id='extract_crm_clients',
        python_callable=extract_crm_clients,
    )
    
    extract_telemetry_task = PythonOperator(
        task_id='extract_telemetry',
        python_callable=extract_telemetry,
    )
    
    build_daily_task = PythonOperator(
        task_id='build_daily_marts',
        python_callable=build_daily_marts,
    )
    
    build_summary_task = PythonOperator(
        task_id='build_client_summary',
        python_callable=build_client_summary,
    )
    
    verify_task = PythonOperator(
        task_id='verify_and_report',
        python_callable=verify_and_report,
    )
    
    optimize_task = PythonOperator(
        task_id='optimize_tables',
        python_callable=optimize_tables,
    )
    
    [extract_crm_task, extract_telemetry_task] >> build_daily_task >> build_summary_task >> verify_task >> optimize_task
