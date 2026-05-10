import json
from datetime import datetime, timezone
from pathlib import Path

from core.security import redact_secrets


LOG_DIR = Path("output/logs")
LOG_FILE = LOG_DIR / "diagnostics.jsonl"


def log_event(event: str, details: dict | None = None) -> None:
    """Write owner-facing diagnostics without exposing details in the UI."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": redact_secrets(details or {}),
    }

    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")
