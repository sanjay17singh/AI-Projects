from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import true


class Settings(BaseSettings):
    """Single source of app configuration. Every client/service takes this via
    dependency injection — nothing reads os.environ directly outside this file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://localhost:5432/competitor_research"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_model_fast: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # You.com
    youcom_api_key: str = ""
    youcom_base_url: str = "https://ydc-index.io"

    # Serper.dev — optional second, independent search provider. Explicit
    # SERPER_ENABLED toggle so it can be turned off even when a key is
    # configured (e.g. for cost control), in addition to the natural
    # graceful-degradation-if-no-key behavior.
    serper_enabled: bool = False
    serper_api_key: str = ""
    serper_base_url: str = "https://google.serper.dev"

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "competitor-research"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_embedding_dimension: int = 1536

    # LangSmith (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "market-research-agent"

    # Future AGI (optional) — a second, independent tracing/eval/simulation
    # layer that runs alongside LangSmith, not instead of it. Explicit
    # FUTUREAGI_ENABLED toggle, same reasoning as SERPER_ENABLED: turning it
    # off must not require deleting the keys.
    futureagi_enabled: bool = true
    fi_api_key: str = ""
    fi_secret_key: str = ""
    fi_project_name: str = "market-research-agent"

    # App
    backend_base_url: str = "http://localhost:8000"
    app_env: str = "development"
    log_level: str = "INFO"
    default_budget_usd_limit: float = 5.00
    coverage_threshold: float = 0.6
    max_retries_per_competitor: int = 2
    max_gap_retries: int = 3
    max_discovery_retries: int = 2

    # Retrieval/extraction knobs — previously hardcoded module constants.
    # Exposed here (same defaults as before) so an evaluation run can sweep
    # them (e.g. top_k=5 vs top_k=8) without editing source.
    retrieval_top_k: int = 6
    extraction_temperature: float = 0.0
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # Tests only
    test_database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
