import os
import re
from typing import Any


SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password|authorization)\s*[:=]\s*['\"]?[^'\"\s,}]+"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._\-]+"),
    re.compile(r"(?i)(key=)[a-z0-9._\-]+"),
    re.compile(r"(?i)(access_token=)[^&\s]+"),
    re.compile(r"(?i)(refresh_token=)[^&\s]+"),
    re.compile(r"(?i)(password=)[^&\s]+"),
    re.compile(r"\b(sk|re|tvly|ghp|github_pat)-[A-Za-z0-9._\-]{8,}\b"),
    re.compile(r"\b(re|tvly|ghp|github_pat)_[A-Za-z0-9._\-]{8,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9._\-]{20,}\b"),
)


def _secret_values() -> list[str]:
    values = []
    for key, value in os.environ.items():
        if not value or len(value) < 8:
            continue

        key_lower = key.lower()
        if any(marker in key_lower for marker in ("key", "secret", "token", "password")):
            values.append(value)

    return values


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: redact_secrets(v) for k, v in value.items()}

    if isinstance(value, list):
        return [redact_secrets(item) for item in value]

    if not isinstance(value, str):
        return value

    redacted = value
    for secret in _secret_values():
        redacted = redacted.replace(secret, "[REDACTED]")

    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: _redact_match(match), redacted)

    return redacted


def _redact_match(match: re.Match) -> str:
    text = match.group(0)
    if ":" in text:
        return f"{text.split(':', 1)[0]}: [REDACTED]"
    if "=" in text:
        return f"{text.split('=', 1)[0]}=[REDACTED]"
    if text.lower().startswith("bearer "):
        return "Bearer [REDACTED]"
    return "[REDACTED]"


def public_error(message: str = "Something went wrong. Please try again.") -> str:
    return message


def safe_exception(exc: Exception) -> str:
    return str(redact_secrets(str(exc)))
