from __future__ import annotations

import re


SECRET_PATH_PATTERNS = (
    "/var/run/secrets",
    "/run/secrets",
    "/etc/kubernetes",
    "/etc/rancher",
)

SENSITIVE_KEY_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)\b"
)
ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)"
    r"\s*[:=]\s*([^\s,;]+)"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
LONG_SECRETISH_RE = re.compile(r"\b[A-Za-z0-9+/=_-]{48,}\b")


def redact_text(value: str) -> str:
    text = value
    for secret_path in SECRET_PATH_PATTERNS:
        text = text.replace(secret_path, "[REDACTED_SECRET_PATH]")
    text = ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = BEARER_RE.sub("Bearer [REDACTED]", text)
    text = LONG_SECRETISH_RE.sub("[REDACTED_LONG_VALUE]", text)
    return text


def redact_value(value: object) -> object:
    if isinstance(value, str):
        if SENSITIVE_KEY_RE.search(value):
            return redact_text(value)
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, dict):
        redacted: dict[object, object] = {}
        for key, item in value.items():
            if isinstance(key, str) and SENSITIVE_KEY_RE.search(key):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_value(item)
        return redacted
    return value


def cap_text(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    clipped = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return f"{clipped}\n[TRUNCATED_TO_{max_bytes}_BYTES]"
