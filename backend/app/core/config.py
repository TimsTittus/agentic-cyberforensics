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
    DATABASE_URL: str  # "postgresql+asyncpg://user:pass@host:5432/db"

    NEO4J_URI: str  # "bolt://neo4j:7687"
    NEO4J_USER: str
    NEO4J_PASSWORD: SecretStr

    QDRANT_HOST: str
    QDRANT_PORT: int = 6333

    REDIS_URL: str  # "redis://redis:6379/0"

    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    APP_NAME: str = "AgentBruce"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()