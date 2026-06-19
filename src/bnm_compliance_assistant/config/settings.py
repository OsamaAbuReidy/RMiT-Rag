from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    embedding_provider: str = "openai"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = 1536
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "bnm_compliance_chunks"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_candidate_count: int = 20
    app_env: str = "local"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
