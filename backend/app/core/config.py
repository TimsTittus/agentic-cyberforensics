"""
AgentBruce — Application Configuration

Pydantic BaseSettings with strict typing for all database URIs,
API keys, and security secrets. Values are loaded from environment
variables and the root `.env` file.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Centralized, strictly-typed application configuration."""
    DATABASE_URL: str = "postgresql+asyncpg://bruce:bruceforensics@localhost:5435/agentbruce"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("bruceforensics")

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    REDIS_URL: str = "redis://localhost:6381/0"

    JWT_SECRET_KEY: SecretStr = SecretStr("09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    APP_NAME: str = "AgentBruce"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    STORAGE_ROOT: str = "/app/storage/evidence"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()