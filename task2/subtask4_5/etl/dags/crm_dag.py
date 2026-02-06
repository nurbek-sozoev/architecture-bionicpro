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
    context['ti'].xcom_push(key='crm_clients_data', value=records)
    return len(records)


def load_crm_to_staging(**context):
    records = context['ti'].xcom_pull(key='crm_clients_data', task_ids='extract_crm_clients')
    
    if not records:
        return 0
    
    columns = [
        'client_id', 'external_id', 'first_name', 'last_name', 
        'email', 'phone', 'country', 'city', 'registration_date', 
        'status', 'prosthesis_serial_number', 'purchase_date',
        'warranty_end_date', 'service_contract_end', 'last_service_date',
        'prosthesis_status'
    ]
    
    inserted = insert_clickhouse_data(
        'analytics.stg_crm_clients',
        records,
        columns
    )
    
    return inserted


def verify_crm_load(**context):
    result = execute_clickhouse_query(
        "SELECT count() FROM analytics.stg_crm_clients WHERE toDate(loaded_at) = today()"
    )
    count = result[0][0] if result else 0
    print(f"Loaded {count} CRM records today")
    return count


with DAG(
    'crm_extract_dag',
    default_args=default_args,
    description='Extract client data from CRM to ClickHouse staging',
    schedule_interval='0 1 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'crm', 'bionicpro'],
) as dag:
    
    extract_task = PythonOperator(
        task_id='extract_crm_clients',
        python_callable=extract_crm_clients,
    )
    
    load_task = PythonOperator(
        task_id='load_crm_to_staging',
        python_callable=load_crm_to_staging,
    )
    
    verify_task = PythonOperator(
        task_id='verify_crm_load',
        python_callable=verify_crm_load,
    )
    
    extract_task >> load_task >> verify_task
