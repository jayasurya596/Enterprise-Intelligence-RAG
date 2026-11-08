from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    default_domain: str = "financial"
    app_secret_key: str = "development-only-change-me-before-sharing"
    database_url: str = "sqlite:///./data/enterprise_rag.db"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    upload_dir: Path = Path("./data/uploads")
    max_upload_mb: int = 25
    chunk_size_chars: int = 3200
    chunk_overlap_chars: int = 480
    embedding_provider: str = "hashing"
    embedding_model: str = "hashing-v1"
    embedding_dimensions: int = 384
    min_dense_score: float = 0.2
    reranker_provider: str = "none"
    reranker_model: str = "BAAI/bge-reranker-base"
    generation_provider: str = "local"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    top_k_dense: int = 20
    top_k_bm25: int = 20
    top_k_rerank: int = 8
    rrf_k: int = 60
    access_token_minutes: int = 45
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

