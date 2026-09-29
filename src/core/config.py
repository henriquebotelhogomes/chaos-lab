from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Chaos Lab (ShopCore API)"
    app_version: str = "1.0.0"
    app_env: str = "production"
    port: int = 8080
    host: str = "0.0.0.0"

    # Datadog APM Settings
    dd_service: str = "chaos-lab"
    dd_env: str = "production"
    dd_version: str = "1.0.0"
    dd_agent_host: str = "localhost"
    dd_trace_enabled: bool = False

    # OpsMesh Webhook Link
    opsmesh_url: str = "https://opsmesh-197215016090.us-central1.run.app"

    # Simulated Database Config
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_timeout_seconds: float = 3.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
