from datetime import date
from typing import Any, Optional
import clickhouse_connect

from app.config import settings


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def execute_query(query: str, parameters: dict | None = None) -> list[dict[str, Any]]:
    client = get_clickhouse_client()
    result = client.query(query, parameters=parameters)
    columns = result.column_names
    rows = result.result_rows
    return [dict(zip(columns, row)) for row in rows]


def get_last_processed_date() -> Optional[date]:
    query = """
        SELECT last_processed_date 
        FROM analytics.etl_metadata FINAL
        WHERE dag_id = 'transform_load_dag'
        LIMIT 1
    """
    try:
        result = execute_query(query)
        if result and result[0].get("last_processed_date"):
            return result[0]["last_processed_date"]
    except Exception:
        pass
    
    fallback_query = """
        SELECT max(report_date) as max_date
        FROM analytics.dm_client_telemetry_daily
    """
    try:
        result = execute_query(fallback_query)
        if result and result[0].get("max_date"):
            return result[0]["max_date"]
    except Exception:
        pass
    
    return date.today()
