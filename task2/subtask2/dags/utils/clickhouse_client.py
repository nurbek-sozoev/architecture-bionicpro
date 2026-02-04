import os
from clickhouse_driver import Client


def get_clickhouse_client():
    return Client(
        host=os.environ.get('CLICKHOUSE_HOST', 'clickhouse'),
        port=int(os.environ.get('CLICKHOUSE_PORT', 9000)),
        user=os.environ.get('CLICKHOUSE_USER', 'default'),
        password=os.environ.get('CLICKHOUSE_PASSWORD', ''),
        database=os.environ.get('CLICKHOUSE_DB', 'analytics')
    )


def execute_clickhouse_query(query, params=None):
    client = get_clickhouse_client()
    return client.execute(query, params or {})


def insert_clickhouse_data(table, data, columns):
    if not data:
        return 0
    
    client = get_clickhouse_client()
    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES"
    client.execute(query, data)
    return len(data)
