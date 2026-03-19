from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models.history_entry import HistoryEntry


class DatabaseService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS simple_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    recognized_text TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add_entry(self, created_at: str, recognized_text: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO simple_history (created_at, recognized_text)
                VALUES (?, ?)
                """,
                (created_at, recognized_text),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_entries(self, limit: int = 200) -> list[HistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, recognized_text
                FROM simple_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            HistoryEntry(
                id=int(row["id"]),
                created_at=row["created_at"],
                recognized_text=row["recognized_text"],
            )
            for row in rows
        ]
