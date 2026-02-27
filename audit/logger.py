"""
audit/logger.py
Persists every bot action to a local SQLite database.
Table: audit_log (id, timestamp, user, action, app, details, result)

Replace SQLite with PostgreSQL for production by swapping the connection string.
"""
import json
import aiosqlite
from datetime import datetime


DB_PATH = "audit.db"


class AuditLogger:

    async def _ensure_table(self, db):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user      TEXT NOT NULL,
                action    TEXT NOT NULL,
                app       TEXT NOT NULL,
                details   TEXT,
                result    TEXT
            )
        """)
        await db.commit()

    async def log(
        self,
        user: str,
        action: str,
        app: str,
        details: dict = None,
        result: dict = None,
    ):
        """Write a single audit record."""
        async with aiosqlite.connect(DB_PATH) as db:
            await self._ensure_table(db)
            await db.execute(
                """
                INSERT INTO audit_log (timestamp, user, action, app, details, result)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    user,
                    action,
                    app,
                    json.dumps(details or {}),
                    json.dumps(result or {}),
                ),
            )
            await db.commit()

    async def get_history(self, app: str, limit: int = 10) -> list[dict]:
        """Return the last N audit records for a given app."""
        async with aiosqlite.connect(DB_PATH) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT timestamp, user, action, result
                FROM audit_log
                WHERE app = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (app, limit),
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                res = json.loads(row["result"] or "{}")
                result.append({
                    "timestamp": row["timestamp"],
                    "user": row["user"],
                    "action": row["action"],
                    "result": res.get("status", "unknown"),
                })
            return result
