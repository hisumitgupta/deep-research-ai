"""
core/rate_limiter.py

Anonymous research rate limiter.

Users do not need an account for the MVP. Instead, the app gives each browser
a small visitor id cookie and allows 5 research reports in a rolling 5-hour
window.
"""

import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components


MAX_WINDOW_RUNS = 5
WINDOW_SECONDS = 5 * 60 * 60
VISITOR_COOKIE_NAME = "dr_visitor"
USAGE_DB_PATH = Path("anonymous_usage.sqlite3")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _cookie_secure_flag() -> str:
    return "; Secure" if os.getenv("APP_ENV", "").lower() == "production" else ""


def _set_browser_cookie(name: str, value: str, max_age_seconds: int) -> None:
    cookie = (
        f"{name}={quote(value)}; path=/; max-age={max_age_seconds}; "
        f"SameSite=Lax{_cookie_secure_flag()}"
    )
    components.html(
        f"<script>document.cookie = {json.dumps(cookie)};</script>",
        height=0,
        width=0,
    )


def get_or_create_visitor_id() -> str:
    visitor_id = st.session_state.get("visitor_id", "").strip()
    cookie_visitor_id = st.context.cookies.get(VISITOR_COOKIE_NAME, "").strip()

    if not visitor_id:
        visitor_id = cookie_visitor_id or secrets.token_urlsafe(24)
        st.session_state.visitor_id = visitor_id

    if cookie_visitor_id != visitor_id:
        _set_browser_cookie(
            VISITOR_COOKIE_NAME,
            visitor_id,
            max_age_seconds=30 * 24 * 60 * 60,
        )

    return visitor_id


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(USAGE_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS anonymous_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL,
            query TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            source_count INTEGER DEFAULT 0,
            searched_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_anonymous_usage_visitor_time
        ON anonymous_usage(visitor_id, searched_at)
        """
    )
    conn.commit()
    return conn


def init_rate_limit_db() -> None:
    with _connect():
        return None


def _delete_old_rows(conn: sqlite3.Connection) -> None:
    cutoff = (_now_utc() - timedelta(seconds=WINDOW_SECONDS)).isoformat()
    conn.execute("DELETE FROM anonymous_usage WHERE searched_at < ?", (cutoff,))
    conn.commit()


def _window_rows(conn: sqlite3.Connection, visitor_id: str) -> list[tuple[str]]:
    cutoff = (_now_utc() - timedelta(seconds=WINDOW_SECONDS)).isoformat()
    cursor = conn.execute(
        """
        SELECT searched_at
        FROM anonymous_usage
        WHERE visitor_id = ? AND searched_at >= ?
        ORDER BY searched_at ASC
        """,
        (visitor_id, cutoff),
    )
    return cursor.fetchall()


def _seconds_until_reset(rows: list[tuple[str]]) -> int:
    if not rows:
        return 0

    oldest_time = datetime.fromisoformat(rows[0][0])
    reset_time = oldest_time + timedelta(seconds=WINDOW_SECONDS)
    seconds = int((reset_time - _now_utc()).total_seconds())
    return max(0, seconds)


def _format_wait(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours and minutes:
        return f"{hours} hour {minutes} minutes"
    if hours:
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    return f"{max(1, minutes)} minute" if minutes <= 1 else f"{minutes} minutes"


def get_user_stats(visitor_id: str) -> dict:
    if not visitor_id:
        return {
            "runs_today": 0,
            "runs_remaining": MAX_WINDOW_RUNS,
            "total_runs": 0,
            "daily_limit": MAX_WINDOW_RUNS,
            "reset_after_seconds": 0,
        }

    with _connect() as conn:
        _delete_old_rows(conn)
        rows = _window_rows(conn, visitor_id)
        runs_used = len(rows)

        return {
            "runs_today": runs_used,
            "runs_remaining": max(0, MAX_WINDOW_RUNS - runs_used),
            "total_runs": runs_used,
            "daily_limit": MAX_WINDOW_RUNS,
            "reset_after_seconds": _seconds_until_reset(rows),
        }


def check_rate_limit(visitor_id: str) -> dict:
    if not visitor_id:
        return {
            "allowed": False,
            "reason": "Could not identify this browser session. Please refresh and try again.",
            "runs_today": 0,
            "runs_remaining": 0,
        }

    with _connect() as conn:
        _delete_old_rows(conn)
        rows = _window_rows(conn, visitor_id)
        runs_used = len(rows)

        if runs_used >= MAX_WINDOW_RUNS:
            wait_seconds = _seconds_until_reset(rows)
            return {
                "allowed": False,
                "reason": (
                    "Too much traffic from this browser. "
                    f"You can generate 5 reports every 5 hours. Please come back in {_format_wait(wait_seconds)}."
                ),
                "runs_today": runs_used,
                "runs_remaining": 0,
                "reset_after_seconds": wait_seconds,
            }

        return {
            "allowed": True,
            "runs_today": runs_used,
            "runs_remaining": MAX_WINDOW_RUNS - runs_used,
            "reset_after_seconds": _seconds_until_reset(rows),
        }


def log_research_run(visitor_id: str, query: str, result: dict) -> None:
    if not visitor_id:
        print("[Rate Limiter] Missing visitor id, usage not logged.")
        return

    with _connect() as conn:
        _delete_old_rows(conn)
        conn.execute(
            """
            INSERT INTO anonymous_usage (visitor_id, query, score, source_count, searched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                visitor_id,
                query[:300],
                result.get("score", 0),
                result.get("source_count", 0),
                _now_utc().isoformat(),
            ),
        )
        conn.commit()
