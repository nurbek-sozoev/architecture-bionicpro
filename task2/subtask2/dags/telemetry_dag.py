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


def extract_telemetry(**context):
    execution_date = context['execution_date']
    date_from = execution_date - timedelta(days=1)
    date_to = execution_date
    
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
    context['ti'].xcom_push(key='telemetry_data', value=records)
    return len(records)


def load_telemetry_to_staging(**context):
    records = context['ti'].xcom_pull(key='telemetry_data', task_ids='extract_telemetry')
    
    if not records:
        return 0
    
    columns = [
        'telemetry_id', 'prosthesis_serial_number', 'prosthesis_model',
        'recorded_at', 'battery_level', 'response_time_ms', 'grip_strength',
        'myosignal_amplitude', 'movements_count', 'temperature', 'error_code'
    ]
    
    inserted = insert_clickhouse_data(
        'analytics.stg_telemetry',
        records,
        columns
    )
    
    return inserted


def verify_telemetry_load(**context):
    result = execute_clickhouse_query(
        "SELECT count() FROM analytics.stg_telemetry WHERE toDate(loaded_at) = today()"
    )
    count = result[0][0] if result else 0
    print(f"Loaded {count} telemetry records today")
    return count


with DAG(
    'telemetry_extract_dag',
    default_args=default_args,
    description='Extract telemetry data from PostgreSQL to ClickHouse staging',
    schedule_interval='30 1 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'telemetry', 'bionicpro'],
) as dag:
    
    extract_task = PythonOperator(
        task_id='extract_telemetry',
        python_callable=extract_telemetry,
    )
    
    load_task = PythonOperator(
        task_id='load_telemetry_to_staging',
        python_callable=load_telemetry_to_staging,
    )
    
    verify_task = PythonOperator(
        task_id='verify_telemetry_load',
        python_callable=verify_telemetry_load,
    )
    
    extract_task >> load_task >> verify_task
