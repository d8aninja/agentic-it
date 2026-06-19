"""
Persists each agent run to a local SQLite database at logs/agent_runs.db.
"""

import sqlite3
import pathlib
from datetime import datetime, timezone

DB_PATH = pathlib.Path(__file__).parent.parent / "logs" / "agent_runs.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    user_input  TEXT    NOT NULL,
    diagnosis   TEXT,
    action      TEXT,
    success     INTEGER NOT NULL,
    output      TEXT
);
"""


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def log_run(
    user_input: str,
    diagnosis: str,
    action: str,
    success: bool,
    output: str,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (ts, user_input, diagnosis, action, success, output) VALUES (?,?,?,?,?,?)",
            (ts, user_input, diagnosis, action, int(success), output),
        )


def get_recent_runs(limit: int = 20) -> list[dict]:
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT id, ts, user_input, diagnosis, action, success, output FROM runs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]
