from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "analytics"
    
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "reports-realm"
    keycloak_client_id: str = "reports-api"

    class Config:
        env_file = ".env"


settings = Settings()
