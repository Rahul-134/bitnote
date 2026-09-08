import os
from pathlib import Path

# Which backend to use: "sqlite" (default, local file, no setup) or
# "postgres" (needs DATABASE_URL). Anyone running the app with no env vars
# set gets the original local-SQLite behavior unchanged.
DB_PROVIDER = os.getenv("DB_PROVIDER", "sqlite").strip().lower()

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "database" / "bitnote.db"
DB_PATH = os.getenv("BITNOTE_DB_PATH", str(DEFAULT_DB_PATH))


def get_db():
    if DB_PROVIDER == "postgres":
        return _get_postgres_db()
    return _get_sqlite_db()


# ------------------------- SQLite backend (default) -------------------------


def _get_sqlite_db():
    import sqlite3

    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000;")
    return conn


# ------------------------- Postgres backend (opt-in) -------------------------
#
# The rest of the app was written against sqlite3's interface: `?`
# placeholders, `conn.execute(sql, params)` as a cursor-creating shortcut,
# `cursor.rowcount`, and rows that support both `row["col"]` and `row[0]`.
# Rather than rewrite ~95 call sites across the app, these wrapper classes
# translate that interface onto psycopg2 so every existing query works
# unchanged on either engine.


def _translate(sql: str) -> str:
    # sqlite3-style positional placeholders (?) -> psycopg2-style (%s).
    # Safe here because no query in this app uses a literal "?" character.
    return sql.replace("?", "%s")


class _PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        self._cursor.execute(_translate(sql), params)
        return self

    def executemany(self, sql, seq_of_params):
        self._cursor.executemany(_translate(sql), seq_of_params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class _PostgresConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cursor = self._conn.cursor()
        cursor.execute(_translate(sql), params)
        return _PostgresCursor(cursor)

    def cursor(self):
        return _PostgresCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _get_postgres_db():
    import psycopg2
    import psycopg2.extras

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DB_PROVIDER=postgres but DATABASE_URL is not set. "
            "Add it to your .env file (see .env.example)."
        )
    # RealDictCursor rows are real dicts, matching sqlite3.Row's dict-like
    # access (row["col"]) and — importantly — matching how FastAPI's
    # jsonable_encoder serializes them. psycopg2's plain DictCursor rows are
    # secretly a `list` subclass, which jsonable_encoder matches as a bare
    # array before ever trying dict-style access, silently dropping column
    # names from any endpoint that returns raw rows.
    conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
    # Left in psycopg2's default (non-autocommit) transactional mode: every
    # write endpoint in this app already calls db.commit() explicitly, so
    # this matches existing behavior. (Explicitly setting autocommit=True
    # would make conn.commit() a no-op and silently strand the handful of
    # endpoints that issue a literal "BEGIN" before their writes.)
    return _PostgresConnection(conn)
