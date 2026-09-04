import pytest
from sqlalchemy import text

from app.config import Settings
from app.db.models import Base
from app.db.session import get_session_factory

TEST_DATABASE_URL = "postgresql+psycopg://localhost/agentgate_test"


@pytest.fixture
def test_settings() -> Settings:
    return Settings(database_url=TEST_DATABASE_URL, pinecone_api_key="", openai_api_key="")


@pytest.fixture
def session_factory(test_settings):
    return get_session_factory(test_settings)


@pytest.fixture(autouse=True)
def clean_business_tables(session_factory):
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with session_factory.session() as session:
        session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        session.commit()
    yield
