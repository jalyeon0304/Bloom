from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bloom"
    app_env: str = "dev"
    log_level: str = "INFO"

    webview_base_url: str = "https://webview.example.local"
    webview_username: str = ""
    webview_password: str = ""

    database_url: str = "postgresql+psycopg://bloom:bloom@localhost:5432/bloom"
    crawl_interval_seconds: int = 60
    timezone: str = "Asia/Seoul"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
