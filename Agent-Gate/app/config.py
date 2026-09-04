"""Centralized application settings.

All external configuration flows through this module. No other module should
read `os.environ` directly — inject a `Settings` instance instead so tests can
swap configuration without mutating process environment.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"

    database_url: str = "postgresql+psycopg://localhost/agentgate"

    pinecone_api_key: str = ""
    pinecone_index_name: str = "agentgate"
    pinecone_namespace_prefix: str = "agentgate"

    langsmith_api_key: str = ""
    langsmith_project: str = "agentgate-development"
    langsmith_tracing: bool = False

    app_env: str = "development"
    log_level: str = "INFO"
    default_scenario_budget: int = Field(default=40, ge=1)

    @property
    def psycopg_dsn(self) -> str:
        """Plain psycopg DSN (no SQLAlchemy driver prefix) for the LangGraph checkpointer."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
