from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from app.config import settings


def database_path() -> Path:
    url = settings.database_url.strip()
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("MVP supports SQLite DATABASE_URL values only")
    raw_path = url[len(prefix):]
    if not raw_path or raw_path == ":memory:" or "?" in raw_path:
        raise ValueError("DATABASE_URL must point to a persistent SQLite file")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    return con


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with database() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA synchronous = NORMAL")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_updated_at ON campaigns(updated_at)")
