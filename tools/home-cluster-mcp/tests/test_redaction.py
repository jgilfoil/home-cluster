from home_cluster_mcp.redaction import cap_text, redact_text, redact_value


def test_redacts_secret_assignments_and_bearer_tokens() -> None:
    text = "password=hunter2 Authorization: Bearer abcdefghijklmnopqrstuvwxyz"

    redacted = redact_text(text)

    assert "hunter2" not in redacted
    assert "abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "[REDACTED]" in redacted


def test_redacts_sensitive_dict_values() -> None:
    data = {"token": "abc123", "message": "ok"}

    assert redact_value(data) == {"token": "[REDACTED]", "message": "ok"}


def test_caps_text_by_bytes() -> None:
    capped = cap_text("abcdef", 3)

    assert capped.startswith("abc")
    assert "[TRUNCATED_TO_3_BYTES]" in capped
