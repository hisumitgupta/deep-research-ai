import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


class SupabaseConfigError(Exception):
    pass


def _get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise SupabaseConfigError(f"Missing required environment variable: {name}")

    return value


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    supabase_url = _get_required_env("SUPABASE_URL")
    supabase_key = _get_required_env("SUPABASE_ANON_KEY")

    return create_client(supabase_url, supabase_key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    supabase_url = _get_required_env("SUPABASE_URL")
    service_key = _get_required_env("SUPABASE_SERVICE_ROLE_KEY")

    return create_client(supabase_url, service_key)


def check_supabase_connection() -> dict:
    try:
        client = get_supabase_client()

        return {
            "ok": True,
            "message": "Supabase client created successfully.",
            "client": client,
        }

    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
            "client": None,
        }
