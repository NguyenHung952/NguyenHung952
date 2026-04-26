from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "slides.db"


def log_event(user_id: int | None, event: str, metadata: str = "") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO usage_events(user_id, event, metadata) VALUES (?, ?, ?)",
            (user_id, event, metadata),
        )
        conn.commit()


def usage_summary(user_id: int) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT event, COUNT(*) FROM usage_events WHERE user_id = ? GROUP BY event",
            (user_id,),
        ).fetchall()
    return {event: count for event, count in rows}
