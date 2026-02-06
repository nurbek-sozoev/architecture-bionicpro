from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

from utils.clickhouse_client import execute_clickhouse_query


default_args = {
    'owner': 'bionicpro-etl',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def build_daily_client_telemetry(**context):
    execution_date = context['execution_date']
    report_date = (execution_date - timedelta(days=1)).strftime('%Y-%m-%d')
    
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
    """
    
    execute_clickhouse_query(query, {'report_date': report_date})
    return f"Built daily telemetry mart for {report_date}"


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
    return "Built client summary mart"


def verify_marts(**context):
    daily_result = execute_clickhouse_query(
        "SELECT count() FROM analytics.dm_client_telemetry_daily WHERE toDate(loaded_at) = today()"
    )
    summary_result = execute_clickhouse_query(
        "SELECT count() FROM analytics.dm_client_summary WHERE toDate(loaded_at) = today()"
    )
    
    daily_count = daily_result[0][0] if daily_result else 0
    summary_count = summary_result[0][0] if summary_result else 0
    
    print(f"Daily telemetry mart: {daily_count} records")
    print(f"Client summary mart: {summary_count} records")
    
    return {'daily': daily_count, 'summary': summary_count}


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
    'transform_load_dag',
    default_args=default_args,
    description='Transform and load data into analytics marts',
    schedule_interval='0 2 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'transform', 'bionicpro'],
) as dag:
    
    wait_crm = ExternalTaskSensor(
        task_id='wait_for_crm_dag',
        external_dag_id='crm_extract_dag',
        external_task_id='verify_crm_load',
        mode='reschedule',
        timeout=3600,
        poke_interval=60,
    )
    
    wait_telemetry = ExternalTaskSensor(
        task_id='wait_for_telemetry_dag',
        external_dag_id='telemetry_extract_dag',
        external_task_id='verify_telemetry_load',
        mode='reschedule',
        timeout=3600,
        poke_interval=60,
    )
    
    build_daily_task = PythonOperator(
        task_id='build_daily_client_telemetry',
        python_callable=build_daily_client_telemetry,
    )
    
    build_summary_task = PythonOperator(
        task_id='build_client_summary',
        python_callable=build_client_summary,
    )
    
    verify_task = PythonOperator(
        task_id='verify_marts',
        python_callable=verify_marts,
    )
    
    optimize_task = PythonOperator(
        task_id='optimize_tables',
        python_callable=optimize_tables,
    )
    
    [wait_crm, wait_telemetry] >> build_daily_task >> build_summary_task >> verify_task >> optimize_task
