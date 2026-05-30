from sqlalchemy import create_engine, inspect, text

from app.database import Base, ensure_sqlite_schema
from app.models import PRReviewTask


def test_ensure_sqlite_schema_adds_missing_model_columns():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE pr_review_task (
                id INTEGER PRIMARY KEY,
                repo_owner VARCHAR(128) NOT NULL,
                repo_name VARCHAR(128) NOT NULL,
                pr_number INTEGER NOT NULL,
                pr_url VARCHAR(512) NOT NULL,
                status VARCHAR(32) NOT NULL
            )
        """))

    ensure_sqlite_schema(engine, Base.metadata)

    columns = {col["name"] for col in inspect(engine).get_columns(PRReviewTask.__tablename__)}
    assert "raw_finding_count" in columns
    assert "deduped_finding_count" in columns
    assert "visible_finding_count" in columns
    assert "github_ready_count" in columns
