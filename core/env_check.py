import os

from dotenv import load_dotenv


load_dotenv()


REQUIRED_ENV_KEYS = {
    "SUPABASE_URL": "Supabase project URL",
    "SUPABASE_ANON_KEY": "Supabase anon public key",
    "SUPABASE_SERVICE_ROLE_KEY": "Supabase server-only service role key",
    "MISTRAL_API_KEY": "Mistral model API key",
    "TAVILY_API_KEY": "Tavily web search API key",
}

OPTIONAL_ENV_KEYS = {
    "NEWS_API_KEY": "NewsAPI current news search",
    "GITHUB_TOKEN": "GitHub repository search",
    "EXA_API_KEY": "Exa semantic search",
    "SESSION_SECRET_KEY": "Production session cookie signing secret",
    "LINKEDIN_ACCESS_TOKEN": "LinkedIn posting",
    "LINKEDIN_PERSON_ID": "LinkedIn profile id",
}


def check_env_keys() -> dict:
    required = []
    optional = []

    for key, label in REQUIRED_ENV_KEYS.items():
        value = os.getenv(key)

        required.append({
            "key": key,
            "label": label,
            "ok": bool(value),
        })

    for key, label in OPTIONAL_ENV_KEYS.items():
        value = os.getenv(key)

        optional.append({
            "key": key,
            "label": label,
            "ok": bool(value),
        })

    missing_required = [
        item["key"]
        for item in required
        if not item["ok"]
    ]

    return {
        "ok": len(missing_required) == 0,
        "missing_required": missing_required,
        "required": required,
        "optional": optional,
    }


def format_missing_env_message(status: dict) -> str:
    if status["ok"]:
        return "All required environment variables are configured."

    missing = ", ".join(status["missing_required"])

    return f"Missing required environment variables: {missing}"
