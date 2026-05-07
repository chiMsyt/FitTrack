# config/db.py
# =============================================================================
# Database connection manager for FitTrack.
#
# Design decisions:
#   - Singleton pattern: only one connection pool is created per app session.
#   - Context manager support: allows `with get_cursor() as cursor:` blocks,
#     which guarantees cursors are closed and transactions are committed or
#     rolled back automatically — no manual cleanup needed in model files.
#   - Credentials are loaded from .env via python-dotenv, never hardcoded.
#   - All DB errors are caught here and re-raised as a single DBError type
#     so the rest of the app only needs to handle one exception class.
# =============================================================================

import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

load_dotenv()  # reads .env file from project root


class DBError(Exception):
    """Raised whenever a database operation fails. Wraps MySQLError."""
    pass


class _ConnectionManager:
    """
    Internal singleton that holds the active MySQL connection.
    Do not instantiate this directly — use the module-level functions below.
    """

    def __init__(self):
        self._connection: mysql.connector.MySQLConnection | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the MySQL connection using credentials from .env."""
        try:
            self._connection = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                database=os.getenv("DB_NAME", "fittrack_db"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                autocommit=False,           # we commit explicitly per operation
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
                connection_timeout=10,
            )
        except MySQLError as e:
            raise DBError(
                f"Could not connect to MySQL.\n"
                f"Check your .env credentials and that MySQL 9.7 is running.\n"
                f"Detail: {e}"
            ) from e

    def disconnect(self) -> None:
        """Close the connection gracefully if it is open."""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None

    def _ensure_connected(self) -> None:
        """Re-connect automatically if the connection was lost (e.g. timeout)."""
        if self._connection is None or not self._connection.is_connected():
            self.connect()

    # ------------------------------------------------------------------
    # Cursor context manager
    # ------------------------------------------------------------------

    @contextmanager
    def cursor(self, dictionary: bool = True):
        """
        Yield a database cursor inside a managed transaction block.

        Usage in model files:
            with db.cursor() as cur:
                cur.execute("SELECT ...")
                return cur.fetchall()

        - dictionary=True  → rows returned as dicts (column name as key)
        - dictionary=False → rows returned as tuples (for single-value fetches)
        - On success  → commits automatically.
        - On any error → rolls back and re-raises as DBError.
        """
        self._ensure_connected()
        cur = self._connection.cursor(dictionary=dictionary)
        try:
            yield cur
            self._connection.commit()
        except MySQLError as e:
            self._connection.rollback()
            raise DBError(f"Database operation failed: {e}") from e
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cur.close()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the database is reachable, False otherwise."""
        try:
            self._ensure_connected()
            self._connection.ping(reconnect=True, attempts=2, delay=1)
            return True
        except (MySQLError, DBError):
            return False


# Module-level singleton — import this everywhere
db = _ConnectionManager()
