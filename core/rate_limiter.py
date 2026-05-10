"""
core/rate_limiter.py

Supabase-backed rate limiter.

This file controls how many research reports a user can generate.
It uses the Supabase usage_log table instead of local SQLite.
"""

from datetime import datetime, timezone

from core.security import safe_exception
from core.supabase_client import get_supabase_admin_client


MAX_DAILY_RUNS = 5
MIN_GAP_SECONDS = 60


def init_rate_limit_db() -> None:
    return None


def _today_start_utc() -> str:
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    return start.isoformat()


def _parse_supabase_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")

    return datetime.fromisoformat(value)


def get_user_stats(user_id: str) -> dict:
    if not user_id:
        return {
            "runs_today": 0,
            "runs_remaining": MAX_DAILY_RUNS,
            "total_runs": 0,
            "daily_limit": MAX_DAILY_RUNS,
        }

    try:
        supabase = get_supabase_admin_client()
        today_start = _today_start_utc()

        today_response = (
            supabase
            .table("usage_log")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("searched_at", today_start)
            .execute()
        )

        total_response = (
            supabase
            .table("usage_log")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        runs_today = today_response.count or 0
        total_runs = total_response.count or 0

        return {
            "runs_today": runs_today,
            "runs_remaining": max(0, MAX_DAILY_RUNS - runs_today),
            "total_runs": total_runs,
            "daily_limit": MAX_DAILY_RUNS,
        }

    except Exception as e:
        print(f"[Rate Limiter] Supabase stats error: {safe_exception(e)}")
        return {
            "runs_today": 0,
            "runs_remaining": MAX_DAILY_RUNS,
            "total_runs": 0,
            "daily_limit": MAX_DAILY_RUNS,
        }


def check_rate_limit(user_id: str) -> dict:
    if not user_id:
        return {
            "allowed": False,
            "reason": "Please login before running research.",
            "runs_today": 0,
            "runs_remaining": 0,
        }

    try:
        supabase = get_supabase_admin_client()
        today_start = _today_start_utc()

        response = (
            supabase
            .table("usage_log")
            .select("searched_at", count="exact")
            .eq("user_id", user_id)
            .gte("searched_at", today_start)
            .order("searched_at", desc=True)
            .limit(1)
            .execute()
        )

        runs_today = response.count or 0
        latest_rows = response.data or []

        if runs_today >= MAX_DAILY_RUNS:
            return {
                "allowed": False,
                "reason": f"You have used all {MAX_DAILY_RUNS} research credits for today.",
                "runs_today": runs_today,
                "runs_remaining": 0,
            }

        if latest_rows:
            last_run_time = _parse_supabase_time(latest_rows[0]["searched_at"])
            gap_seconds = (datetime.now(timezone.utc) - last_run_time).total_seconds()

            if gap_seconds < MIN_GAP_SECONDS:
                wait = int(MIN_GAP_SECONDS - gap_seconds)

                return {
                    "allowed": False,
                    "reason": f"Please wait {wait} more seconds before your next search.",
                    "runs_today": runs_today,
                    "runs_remaining": MAX_DAILY_RUNS - runs_today,
                }

        return {
            "allowed": True,
            "runs_today": runs_today,
            "runs_remaining": MAX_DAILY_RUNS - runs_today,
        }

    except Exception as e:
        print(f"[Rate Limiter] Supabase check error: {safe_exception(e)}")
        return {
            "allowed": False,
            "reason": "Could not check usage limit. Please try again.",
            "runs_today": 0,
            "runs_remaining": 0,
        }


def log_research_run(user_id: str, query: str, result: dict) -> None:
    if not user_id:
        print("[Rate Limiter] Missing user_id, usage not logged.")
        return

    try:
        supabase = get_supabase_admin_client()

        row = {
            "user_id": user_id,
            "query": query[:300],
            "score": result.get("score", 0),
            "source_count": result.get("source_count", 0),
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("usage_log").insert(row).execute()

        print(f"[Rate Limiter] Supabase run logged for: {user_id}")

    except Exception as e:
        print(f"[Rate Limiter] Failed to log Supabase usage: {safe_exception(e)}")
