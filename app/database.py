from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema(engine, Base.metadata)


def ensure_sqlite_schema(bind, metadata):
    """Add model columns missing from existing SQLite tables.

    This project uses SQLite for demos and local judging. SQLAlchemy create_all()
    creates missing tables but does not migrate older tables, so lightweight
    additive migration keeps existing demo databases usable.
    """
    if bind.dialect.name != "sqlite":
        return

    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    with bind.begin() as conn:
        for table in metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_columns = {
                column["name"] for column in inspector.get_columns(table.name)
            }
            for column in table.columns:
                if column.name in existing_columns:
                    continue

                column_type = column.type.compile(dialect=bind.dialect)
                default_sql = _sqlite_default_sql(column)
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}{default_sql}'
                conn.execute(text(ddl))


def _sqlite_default_sql(column):
    default = column.default
    if default is None or default.is_callable:
        return ""

    value = default.arg
    if isinstance(value, bool):
        return f" DEFAULT {1 if value else 0}"
    if isinstance(value, (int, float)):
        return f" DEFAULT {value}"
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f" DEFAULT '{escaped}'"
    return ""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
