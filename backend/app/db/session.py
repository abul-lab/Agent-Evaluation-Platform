"""Database session and connection management."""

from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)


def init_db() -> None:
    """Initialize database tables and set SQLite pragmas."""
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA foreign_keys=ON;"))
            try:
                eval_info = conn.execute(text("PRAGMA table_info(evaluations);")).fetchall()
                eval_cols = {row[1] for row in eval_info}
                if eval_info and "semantic_json" not in eval_cols:
                    conn.execute(text("ALTER TABLE evaluations ADD COLUMN semantic_json TEXT;"))
                if eval_info and "workspace_id" not in eval_cols:
                    conn.execute(
                        text("ALTER TABLE evaluations ADD COLUMN workspace_id VARCHAR(36);")
                    )

                trace_info = conn.execute(text("PRAGMA table_info(traces);")).fetchall()
                trace_cols = {row[1] for row in trace_info}
                if trace_info and "workspace_id" not in trace_cols:
                    conn.execute(text("ALTER TABLE traces ADD COLUMN workspace_id VARCHAR(36);"))
                conn.commit()
            except Exception:
                pass
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    with Session(engine) as session:
        yield session


def check_db_health() -> str:
    """Check database connectivity and return status string."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return "connected"
    except Exception:
        return "disconnected"
