"""Connection to Lakebase (Postgres).

Lakebase has no fixed password. Whoever connects (the app's service principal when
deployed, or you on your Mac) proves who they are with a short-lived OAuth token
from Databricks. We fetch a fresh token every time the pool opens a new connection.
"""

import os
import threading
import time
from contextlib import contextmanager

import psycopg
from databricks.sdk import WorkspaceClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# Which Lakebase compute endpoint to talk to. Deployed: set per target in
# databricks.yml (apps -> config -> env). Locally: set by scripts/dev.sh.
ENDPOINT = os.environ.get(
    "LAKEBASE_ENDPOINT", "projects/matchmaker/branches/production/endpoints/primary"
)

_workspace: WorkspaceClient | None = None
_token: str | None = None
_token_expires_at = 0.0
_token_lock = threading.Lock()


def _ws() -> WorkspaceClient:
    """Databricks SDK client. Deployed: authenticates as the app's service principal.
    Locally: uses the CLI profile in DATABRICKS_CONFIG_PROFILE (koantek-free)."""
    global _workspace
    if _workspace is None:
        _workspace = WorkspaceClient()
    return _workspace


def _get_token() -> str:
    """Return a cached Lakebase OAuth token, refreshing it ~10 minutes before it expires."""
    global _token, _token_expires_at
    with _token_lock:
        if _token is None or time.time() > _token_expires_at - 600:
            cred = _ws().postgres.generate_database_credential(endpoint=ENDPOINT)
            _token = cred.token
            _token_expires_at = time.time() + 3600  # tokens last about an hour
        return _token


def _conninfo() -> dict:
    """Host/user/database. Databricks Apps injects PG* env vars for the database
    resource declared in databricks.yml; we fall back to asking the API."""
    host = os.environ.get("PGHOST")
    if not host:
        host = _ws().postgres.get_endpoint(name=ENDPOINT).status.hosts.host
    user = os.environ.get("PGUSER")
    if not user:
        me = _ws().current_user.me()
        user = me.user_name
    return {
        "host": host,
        "port": int(os.environ.get("PGPORT", "5432")),
        "dbname": os.environ.get("PGDATABASE", "databricks_postgres"),
        "user": user,
        "sslmode": os.environ.get("PGSSLMODE", "require"),
    }


class _OAuthConnection(psycopg.Connection):
    """A normal Postgres connection, except the password is a fresh OAuth token."""

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):
        kwargs["password"] = _get_token()
        return super().connect(conninfo, **kwargs)


_pool: ConnectionPool | None = None


def open_pool() -> None:
    global _pool
    _pool = ConnectionPool(
        connection_class=_OAuthConnection,
        kwargs={**_conninfo(), "row_factory": dict_row},
        min_size=1,
        max_size=5,
        max_lifetime=45 * 60,  # recycle connections before their token would expire
        open=True,  # connects in the background; app still starts if the DB is down
    )


def close_pool() -> None:
    if _pool is not None:
        _pool.close()


@contextmanager
def transaction():
    """Borrow a connection, run everything inside one transaction, give it back.
    Any exception rolls the whole thing back, so we never save half a change."""
    if _pool is None:
        raise RuntimeError("Database pool is not open")
    with _pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                yield cur
