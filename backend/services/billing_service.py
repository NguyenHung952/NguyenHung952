from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "slides.db"


def get_user(user_id: int) -> tuple[int, str]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT credits, plan FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise ValueError("User not found")
    return int(row[0]), str(row[1])


def check_credits(user_id: int, cost: int = 1) -> None:
    credits, plan = get_user(user_id)
    if plan == "pro":
        return
    if credits < cost:
        raise ValueError("Out of credits")


def consume_credits(user_id: int, cost: int = 1) -> None:
    credits, plan = get_user(user_id)
    if plan == "pro":
        return
    next_value = max(0, credits - cost)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET credits = ? WHERE id = ?", (next_value, user_id))
        conn.commit()


def reset_daily_free_quota() -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET credits = 10, last_reset = ? WHERE plan = 'free' AND (last_reset IS NULL OR last_reset != ?)",
            (today, today),
        )
        conn.commit()
