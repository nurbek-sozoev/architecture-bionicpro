from typing import Any
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
