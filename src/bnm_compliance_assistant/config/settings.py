from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = None
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "bnm_compliance_chunks"
    app_env: str = "local"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
