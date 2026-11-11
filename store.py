"""SQLite-хранилище уже увиденных вакансий."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    vacancy_id TEXT    PRIMARY KEY,
    payload    TEXT    NOT NULL,
    first_seen TEXT    NOT NULL,
    notified   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_seen_notified ON seen(notified);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path: str = "state.db"):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    # ── чтение ────────────────────────────────────────────────────────
    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]

    def is_empty(self) -> bool:
        return self.count() == 0

    def known_ids(self) -> set[str]:
        rows = self.conn.execute("SELECT vacancy_id FROM seen").fetchall()
        return {row[0] for row in rows}

    def unnotified(self) -> list[dict]:
        """Запомнены, но не отправлены."""
        rows = self.conn.execute(
            "SELECT payload FROM seen WHERE notified = 0 ORDER BY first_seen, vacancy_id"
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    # ── запись ────────────────────────────────────────────────────────
    def remember(self, vacancies: list[dict], notified: bool = False) -> int:
        """Запоминает новые вакансии. Возвращает количество фактически вставленных."""
        if not vacancies:
            return 0
        now = _utcnow()
        cursor = self.conn.executemany(
            "INSERT OR IGNORE INTO seen (vacancy_id, payload, first_seen, notified) "
            "VALUES (?, ?, ?, ?)",
            [(v["id"], json.dumps(v, ensure_ascii=False), now, int(notified))
             for v in vacancies],
        )
        self.conn.commit()
        return cursor.rowcount

    def mark_notified(self, vacancy_id: str) -> None:
        self.conn.execute(
            "UPDATE seen SET notified = 1 WHERE vacancy_id = ?", (vacancy_id,)
        )
        self.conn.commit()

    def purge_older_than_days(self, days: int = 30) -> int:
        cursor = self.conn.execute(
            "DELETE FROM seen WHERE notified = 1 AND first_seen < datetime('now', ?)",
            (f"-{int(days)} days",),
        )
        self.conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self.conn.close()