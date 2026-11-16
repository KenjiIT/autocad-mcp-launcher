from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from dutoan_mcp.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Create any missing tables (projects, users...) in a downloaded reference-only DB.

    create_all skips tables that already exist, so existing data is untouched.
    """
    import dutoan_mcp.models  # noqa: F401  registers the reference/project tables
    from dutoan_mcp.models import user  # noqa: F401  Project has a foreign key to users

    Base.metadata.create_all(bind=engine, checkfirst=True)
